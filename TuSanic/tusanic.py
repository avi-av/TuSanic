from sanic import Blueprint, request
from sanic import response as Response

from loguru import logger

import uuid
import os
import base64

from TuSanic.tus_file import TusFile, db_session


class Tus:
    def __init__(self, app, upload_folder="uploads"):
        self.app = app
        self.tus_upload_url = "/files"
        self.tus_upload_folder = upload_folder
        self.tus_api_version = '1.0.0'
        self.tus_api_version_supported = '1.0.0'
        self.tus_api_extensions = ['creation', 'termination', 'file-check']
        self.tus_max_file_size = 4294967296  # 4GByte
        self.tus_file_overwrite = True

        self.tus_upload_file_handler_cb = None

        self.__init_endpoints()

    def __init_endpoints(self):
        self.app.add_route(self.tus_file_upload, self.tus_upload_url, methods=[
            'OPTIONS', 'POST', 'GET'])
        self.app.add_route(self.tus_file_upload_chunk,
                           f"{self.tus_upload_url}/<resource_id:string>", methods=['HEAD', 'PATCH', 'DELETE'])
        self.app.register_listener(
            self.delete_temp_files, 'before_server_stop')

    @db_session
    def delete_temp_files(self, *args, **kv):
        logger.info(f"Cleening temp files")
        for File in TusFile.select()[:]:
            os.unlink(os.path.join(self.tus_upload_folder, str(File.fid)))
            File.delete()

    def upload_file_handler(self, callback):
        self.tus_upload_file_handler_cb = callback
        return callback

    def tus_file_upload(self, request: request):
        response = Response.HTTPResponse(status=200)
        logger.info(
            f"Metadata: {request.headers.get('Upload-Metadata', 'None')}")

        if request.method == 'GET':
            metadata = {}
            if "Upload-Metadata" not in request.headers:
                logger.error("Upload-Metadata header is mandatory")
            for kv in request.headers.get("Upload-Metadata").split(","):
                if len(kv.split(" ")) > 1:
                    key, value = kv.split(" ")
                    metadata[key] = base64.b64decode(value).decode("utf-8")

            if metadata.get("filename", None) is None:
                return Response.text("metadata filename is not set", 404)

            (filename_name, _) = os.path.splitext(
                metadata.get("filename"))
            if filename_name.upper() in [os.path.splitext(f)[0].upper() for f in os.listdir(os.path.dirname(self.tus_upload_folder))]:
                response.headers['Tus-File-Name'] = metadata.get("filename")
                response.headers['Tus-File-Exists'] = True
            else:
                response.headers['Tus-File-Exists'] = False
            return response

        elif request.method == 'OPTIONS' and 'Access-Control-Request-Method' in request.headers:
            # CORS option request, return 200
            return response

        if request.headers.get("Tus-Resumable") is not None:
            response.headers['Tus-Resumable'] = self.tus_api_version
            response.headers['Tus-Version'] = self.tus_api_version_supported

            if request.method == 'OPTIONS':
                response.headers['Tus-Extension'] = ",".join(
                    self.tus_api_extensions)
                response.headers['Tus-Max-Size'] = self.tus_max_file_size

                response.status = 204
                return response

            # process upload metadata
            metadata = {}
            if "Upload-Metadata" not in request.headers:
                logger.error("Upload-Metadata header is mandatory")
            for kv in request.headers.get("Upload-Metadata").split(","):
                if len(kv.split(" ")) > 1:
                    key, value = kv.split(" ")
                    metadata[key] = base64.b64decode(value).decode("utf-8")

            if metadata.get("filename") and os.path.lexists(os.path.join(self.tus_upload_folder, metadata.get("filename"))) and self.tus_file_overwrite is False:
                response.status = 409
                return response

            file_size = int(request.headers.get("Upload-Length", "0"))

            with db_session:
                File = TusFile(
                    filename=metadata.get("filename", " "),
                    file_size=file_size,
                    metadata=metadata
                )

            try:
                f = open(os.path.join(
                    self.tus_upload_folder, str(File.fid)), "w")
                f.seek(file_size - 1)
                f.write("\0")
                f.close()
            except IOError as e:
                logger.error("Unable to create file: {}".format(e))
                response.status = 500
                return response

            response.status = 201
            response.headers['Location'] = '{}/{}'.format(
                request.url, str(File.fid))
            response.headers['Tus-Temp-Filename'] = str(File.fid)

        else:
            logger.warning(
                "Received File upload for unsupported file transfer protocol")
            response.body = b"Received File upload for unsupported file transfer protocol"
            response.status = 500

        return response

    def tus_file_upload_chunk(self, request, resource_id):
        response = Response.HTTPResponse("", 204)

        response.headers['Tus-Resumable'] = self.tus_api_version
        response.headers['Tus-Version'] = self.tus_api_version_supported

        upload_file_path = os.path.join(self.tus_upload_folder, resource_id)

        if request.method == 'HEAD':
            # TODO
            with db_session:
                File = TusFile.get(fid=resource_id)

            if not File or File.offset is None:
                response.status = 404
                return response
            else:
                response.status = 200
                response.headers['Upload-Offset'] = File.offset
                response.headers['Cache-Control'] = 'no-store'
                return response

        if request.method == 'DELETE':
            os.unlink(upload_file_path)
            with db_session:
                TusFile[resource_id].delete()

            response.status = 204
            return response

        if request.method == 'PATCH':
            with db_session:
                File = TusFile.get(fid=resource_id)

            if File.filename is None or os.path.lexists(upload_file_path) is False:
                logger.info(
                    "PATCH sent for resource_id that does not exist. {}".format(resource_id))
                response.status = 410
                return response

            file_offset = int(request.headers.get("Upload-Offset", 0))
            chunk_size = int(request.headers.get("Content-Length", 0))

            # check to make sure we're in sync
            if file_offset != File.offset:
                response.status = 409  # HTTP 409 Conflict
                return response

            try:
                f = open(upload_file_path, "r+b")
            except IOError:
                f = open(upload_file_path, "wb")
            finally:
                f.seek(file_offset)
                f.write(request.body)
                f.close()

            with db_session:
                File = TusFile[resource_id]
                new_offset = File.offset + chunk_size
                File.set(offset=new_offset)

            response.headers['Upload-Offset'] = new_offset
            response.headers['Tus-Temp-Filename'] = resource_id

            if File.file_size == new_offset:  # file transfer complete, rename from resource id to actual filename
                if callable(self.tus_upload_file_handler_cb):
                    self.tus_upload_file_handler_cb(
                        upload_file_path, File.filename)
                else:
                    os.rename(upload_file_path, os.path.join(
                        self.tus_upload_folder, File.filename))

                with db_session:
                    TusFile[resource_id].delete()

            return response
