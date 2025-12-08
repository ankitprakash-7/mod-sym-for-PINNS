FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

WORKDIR /home
# gcloud Installation.
# ARG CLOUD_SDK_VERSION=322.0.0
# ENV GCLOUD_HOME=/opt/google-cloud-sdk
# ENV PATH="${GCLOUD_HOME}/bin/:${PATH}"
# RUN DOWNLOAD_URL="https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz" \
#     && TMP_DIR="$(mktemp -d)" \
#     && curl -fL "${DOWNLOAD_URL}" --output "${TMP_DIR}/google-cloud-sdk.tar.gz" \
#     && mkdir -p "${GCLOUD_HOME}" \
#     && tar xzf "${TMP_DIR}/google-cloud-sdk.tar.gz" -C "${GCLOUD_HOME}" --strip-components=1 \
#     && "${GCLOUD_HOME}/install.sh" \
#     --bash-completion=false \
#     --path-update=false \
#     --usage-reporting=false \
#     --additional-components alpha beta kubectl \
#     --quiet \
#     && rm -rf "${TMP_DIR}" \
#     && gcloud --version


RUN apt-get update && apt-get install -y unzip

COPY . /home

RUN pip install --no-cache-dir --upgrade -r /home/requirements.txt

EXPOSE 8000

CMD ["sh","-c", "python3 /home/app.py"]
