"""
Document views — replaces FastAPI document endpoints.
"""

import json
import os
import shutil
import traceback
from io import BytesIO
from pathlib import Path

import structlog
from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsActiveUser
from .models import Document, DocumentFile, OCRPage
from audit.models import AuditLog
from services.storage import storage_service
from services.ocr import ocr_service

logger = structlog.get_logger()

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
]


# ── helpers ──────────────────────────────────────────────────────────

def _get_document_or_404(document_id, tenant_id):
    """Return a Document scoped to the tenant, or None."""
    try:
        return Document.objects.get(id=document_id, tenant_id=tenant_id)
    except Document.DoesNotExist:
        return None


def _delete_document_files(tenant_id, document_id):
    """Remove physical document and OCR directories."""
    base = str(storage_service.backend.base_path)

    doc_dir = os.path.join(base, f"tenants/{tenant_id}/documents/{document_id}")
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)
        logger.info("document_files_deleted", document_id=document_id, path=doc_dir)

    ocr_dir = os.path.join(base, f"tenants/{tenant_id}/processed/ocr_json/{document_id}")
    if os.path.exists(ocr_dir):
        shutil.rmtree(ocr_dir)
        logger.info("ocr_files_deleted", document_id=document_id, path=ocr_dir)


def _document_dict(doc):
    """Serialize a Document to a plain dict."""
    return {
        "id": doc.id,
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "page_count": doc.page_count,
        "status": doc.status,
        "source": doc.source,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# ── POST / & GET / ──────────────────────────────────────────────────

class DocumentListCreateView(APIView):
    """
    POST / — upload a document.
    GET  / — list documents for current tenant.
    """
    permission_classes = [IsActiveUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # ── POST (upload) ────────────────────────────────────────────────
    def post(self, request):
        from django.conf import settings as django_settings

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size
        if file.size > django_settings.UPLOAD_MAX_SIZE:
            max_mb = django_settings.UPLOAD_MAX_SIZE // (1024 * 1024)
            return Response(
                {"detail": f"File too large. Maximum size is {max_mb}MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sanitize filename
        filename = Path(file.name).name if file.name else f"document_{id(file)}"

        mime_type = file.content_type
        if mime_type not in ALLOWED_MIME_TYPES:
            return Response(
                {"detail": f"File type not supported: {mime_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        language = request.data.get("language", "eng")
        doc_category = request.data.get("doc_category")
        # template_id accepted but unused for now
        # template_id = request.data.get("template_id")

        user = request.user

        # 1. Create Document record
        document = Document.objects.create(
            tenant_id=user.tenant_id,
            filename=file.name,
            mime_type=mime_type,
            status="uploaded",
            source="web_ui",
            created_by_id=user.id,
        )

        try:
            # 2. Save file to storage
            file_path, checksum = storage_service.save_upload(
                file_data=file,
                tenant_id=user.tenant_id,
                document_id=document.id,
                filename=file.name or f"document_{document.id}",
            )

            # 3. Create DocumentFile record
            try:
                DocumentFile.objects.create(
                    document_id=document.id,
                    path=file_path,
                    checksum=checksum,
                    kind="original",
                )
            except Exception as df_error:
                logger.error(
                    "document_file_creation_error",
                    error=str(df_error),
                    error_type=type(df_error).__name__,
                )
                raise

            # 4. Audit log
            AuditLog.objects.create(
                tenant_id=user.tenant_id,
                actor_user_id=user.id,
                action="document_upload",
                entity_type="document",
                entity_id=document.id,
                metadata_json={
                    "filename": file.name,
                    "mime_type": mime_type,
                    "category": doc_category,
                    "file_path": file_path,
                },
            )

            # 5. Trigger OCR processing (synchronous for development)
            try:
                document.status = "processing"
                document.save()

                full_path = storage_service.get_full_path(file_path)
                ocr_results = ocr_service.process_document(full_path, language=language)

                for page_data in ocr_results.get("pages", []):
                    page_num = page_data.get("page_number", 1)
                    json_filename = f"ocr_page_{page_num}.json"
                    json_data = json.dumps(page_data, indent=2).encode("utf-8")
                    json_buffer = BytesIO(json_data)

                    ocr_json_path, _ = storage_service.save_processed(
                        file_data=json_buffer,
                        tenant_id=user.tenant_id,
                        document_id=document.id,
                        filename=json_filename,
                        kind="ocr_json",
                    )

                    OCRPage.objects.create(
                        document_id=document.id,
                        page_no=page_num,
                        engine="tesseract",
                        lang=language,
                        dpi=300,
                        json_path=ocr_json_path,
                    )

                document.status = "extracted"
                document.page_count = ocr_results.get("page_count", 1)
                document.save()

                logger.info("document_processed", document_id=document.id, pages=document.page_count)

            except Exception as ocr_error:
                logger.error("ocr_processing_error", document_id=document.id, error=str(ocr_error))
                document.status = "error"
                document.save()

            return Response(
                {
                    "document_id": document.id,
                    "status": document.status,
                    "message": "Document uploaded successfully and queued for processing",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            error_details = traceback.format_exc()
            logger.error(
                "document_upload_failed",
                error=str(e),
                error_type=type(e).__name__,
                traceback=error_details,
            )
            document.status = "error"
            document.save()
            return Response(
                {"detail": f"Failed to save document: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── GET (list) ───────────────────────────────────────────────────
    def get(self, request):
        user = request.user
        status_filter = request.query_params.get("status")
        limit = min(int(request.query_params.get("limit", 50)), 100)
        offset = max(int(request.query_params.get("offset", 0)), 0)

        qs = Document.objects.filter(tenant_id=user.tenant_id).order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)

        documents = qs[offset : offset + limit]
        return Response([_document_dict(d) for d in documents])


# ── GET /<document_id>/ ─────────────────────────────────────────────

class DocumentDetailView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request, document_id):
        doc = _get_document_or_404(document_id, request.user.tenant_id)
        if not doc:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_document_dict(doc))

    def delete(self, request, document_id):
        """DELETE /<document_id>/ — delete a single document."""
        user = request.user
        doc = _get_document_or_404(document_id, user.tenant_id)
        if not doc:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            _delete_document_files(user.tenant_id, document_id)

            AuditLog.objects.create(
                tenant_id=user.tenant_id,
                actor_user_id=user.id,
                action="document_delete",
                entity_type="document",
                entity_id=doc.id,
                metadata_json={"filename": doc.filename},
            )

            doc.delete()

            logger.info("document_deleted", document_id=document_id, filename=doc.filename)

            return Response({"message": "Document deleted successfully", "document_id": document_id})

        except Exception as e:
            logger.error("document_delete_error", document_id=document_id, error=str(e))
            return Response(
                {"detail": f"Failed to delete document: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ── GET /<document_id>/result ────────────────────────────────────────

class DocumentResultView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request, document_id):
        doc = _get_document_or_404(document_id, request.user.tenant_id)
        if not doc:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        if doc.status != "extracted":
            return Response({
                "document_id": document_id,
                "status": doc.status,
                "message": "Document not yet processed",
                "pages": [],
            })

        ocr_pages = OCRPage.objects.filter(document_id=document_id).order_by("page_no")
        pages_data = []
        full_text_parts = []

        for ocr_page in ocr_pages:
            try:
                full_json_path = storage_service.get_full_path(ocr_page.json_path)
                with open(full_json_path, "r", encoding="utf-8") as f:
                    page_data = json.load(f)
                    pages_data.append(page_data)
                    if page_data.get("text"):
                        full_text_parts.append(page_data["text"])
            except Exception as e:
                logger.error("ocr_json_read_error", page_id=ocr_page.id, error=str(e))
                pages_data.append({
                    "page_number": ocr_page.page_no,
                    "text": "[Error reading OCR data]",
                    "confidence": 0.0,
                })

        return Response({
            "document_id": document_id,
            "status": doc.status,
            "page_count": doc.page_count or len(pages_data),
            "pages": pages_data,
            "full_text": "\n\n".join(full_text_parts),
            "exports": {
                "searchable_pdf": f"/api/v1/documents/{document_id}/download?kind=searchable_pdf",
            },
        })


# ── GET /<document_id>/download ──────────────────────────────────────

class DocumentDownloadView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request, document_id):
        doc = _get_document_or_404(document_id, request.user.tenant_id)
        if not doc:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        kind = request.query_params.get("kind")
        if not kind:
            return Response({"detail": "Query param 'kind' is required."}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.objects.create(
            tenant_id=request.user.tenant_id,
            actor_user_id=request.user.id,
            action="document_download",
            entity_type="document",
            entity_id=doc.id,
            metadata_json={"kind": kind},
        )

        return Response(
            {"detail": "File download not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


# ── GET /<document_id>/pages/<page_num>/image ────────────────────────

class PageImageView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request, document_id, page_num):
        import fitz  # PyMuPDF

        doc = _get_document_or_404(document_id, request.user.tenant_id)
        if not doc:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get the original DocumentFile
        doc_file = DocumentFile.objects.filter(document_id=document_id, kind="original").first()
        if not doc_file:
            return Response({"detail": "Document file not found"}, status=status.HTTP_404_NOT_FOUND)

        # Validate page number
        if page_num < 1 or (doc.page_count and page_num > doc.page_count):
            return Response(
                {"detail": f"Invalid page number. Document has {doc.page_count} pages."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse and clamp DPI
        try:
            dpi = int(request.query_params.get("dpi", 150))
            dpi = max(72, min(300, dpi))
        except (ValueError, TypeError):
            dpi = 150

        try:
            full_path = storage_service.get_full_path(doc_file.path)

            if doc.mime_type == "application/pdf":
                pdf_doc = fitz.open(full_path)
                page = pdf_doc[page_num - 1]

                zoom = dpi / 72
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)
                img_bytes = pix.tobytes("png")
                pdf_doc.close()

                response = HttpResponse(img_bytes, content_type="image/png")
                response["Content-Disposition"] = f"inline; filename=page_{page_num}.png"
                response["Cache-Control"] = "public, max-age=3600"
                return response

            else:
                # For images, return the original file (page 1 only)
                if page_num != 1:
                    return Response(
                        {"detail": "Image documents only have 1 page"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                with open(full_path, "rb") as f:
                    img_bytes = f.read()

                content_type = doc.mime_type or "image/png"
                response = HttpResponse(img_bytes, content_type=content_type)
                response["Content-Disposition"] = f"inline; filename={doc.filename}"
                response["Cache-Control"] = "public, max-age=3600"
                return response

        except Exception as e:
            logger.error("page_image_error", document_id=document_id, page=page_num, error=str(e))
            return Response(
                {"detail": f"Failed to render page image: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ── GET /<document_id>/pages/<page_num>/ocr ──────────────────────────

class PageOCRView(APIView):
    permission_classes = [IsActiveUser]

    def get(self, request, document_id, page_num):
        doc = _get_document_or_404(document_id, request.user.tenant_id)
        if not doc:
            return Response({"detail": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        ocr_page = OCRPage.objects.filter(document_id=document_id, page_no=page_num).first()
        if not ocr_page:
            return Response(
                {"detail": f"OCR data not found for page {page_num}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            full_json_path = storage_service.get_full_path(ocr_page.json_path)
            with open(full_json_path, "r", encoding="utf-8") as f:
                page_data = json.load(f)

            return Response({
                "document_id": document_id,
                "page_number": page_num,
                "dpi": ocr_page.dpi,
                "engine": ocr_page.engine,
                "language": ocr_page.lang,
                "text": page_data.get("text", ""),
                "confidence": page_data.get("confidence", 0.0),
                "words": page_data.get("words_with_coords", []),
                "raw_words": page_data.get("words", []),
            })

        except Exception as e:
            logger.error("page_ocr_read_error", document_id=document_id, page=page_num, error=str(e))
            return Response(
                {"detail": f"Failed to read OCR data: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ── POST /bulk-delete ────────────────────────────────────────────────

class BulkDeleteView(APIView):
    permission_classes = [IsActiveUser]

    def post(self, request):
        document_ids = request.data
        if not isinstance(document_ids, list) or not document_ids:
            return Response(
                {"detail": "No document IDs provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        deleted_count = 0
        errors = []

        for document_id in document_ids:
            try:
                doc = _get_document_or_404(document_id, user.tenant_id)
                if not doc:
                    errors.append(f"Document {document_id} not found")
                    continue

                _delete_document_files(user.tenant_id, document_id)

                AuditLog.objects.create(
                    tenant_id=user.tenant_id,
                    actor_user_id=user.id,
                    action="document_delete",
                    entity_type="document",
                    entity_id=doc.id,
                    metadata_json={"filename": doc.filename, "bulk_delete": True},
                )

                doc.delete()
                deleted_count += 1
                logger.info("document_deleted", document_id=document_id, filename=doc.filename)

            except Exception as e:
                logger.error("document_delete_error", document_id=document_id, error=str(e))
                errors.append(f"Document {document_id}: {str(e)}")

        return Response({
            "message": f"Successfully deleted {deleted_count} document(s)",
            "deleted_count": deleted_count,
            "errors": errors if errors else None,
        })
