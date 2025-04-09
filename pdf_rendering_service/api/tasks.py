import dramatiq
import PIL
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError
from pika.exceptions import ConnectionWrongStateError
import logging

from django.conf import settings
from .models import Document

logger = logging.getLogger(__name__)

@dramatiq.actor
def process_pdf(document_id):

	logger.info("processing document {}".format(document_id))

	
		try:
			document = Document.objects.get(id=document_id)
			pdf_file = settings.MEDIA_ROOT + "document{}.pdf".format(document_id)
			pages = convert_from_path(pdf_file, dpi=200, size=(1200, 1600) )
			for i, page in enumerate(pages):
				png_file =  settings.MEDIA_ROOT + document.get_png_filename(i+1)
				page.save(png_file, 'PNG')
				logger.info(png_file)
			document.status = Document.STATUS_DONE
			document.n_pages = len(pages)
			document.save()
			logger.info("document {} processed successfully !".format(document.id))
		except Document.DoesNotExist:
			logger.error('pdf file does not exist')
			document.status = Document.STATUS_FAILED
			document.save()	
		except PIL.Image.DecompressionBombError:
			logger.error("pdf file too large")
			document.status = Document.STATUS_FAILED
			document.save()	
		except PDFPageCountError:
			logger.error('invalid pdf file')
			document.status = Document.STATUS_FAILED
			document.save()	
		except Exception as e:
			logger.exception(f"An unexpected error occurred: {e}")
			document.status = Document.STATUS_FAILED
			document.save()

	# to avoid "missed heartbeats from client" warnings from rabbitmq, see https://github.com/Bogdanp/django_dramatiq/issues/44
	finally:
		try:
			dramatiq.get_broker().connection.close()
		except ConnectionWrongStateError:
			pass
