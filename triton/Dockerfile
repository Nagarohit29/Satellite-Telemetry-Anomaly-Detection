FROM nvcr.io/nvidia/tritonserver:25.04-py3

LABEL maintainer="Satellite Telemetry Anomaly Detection Team"
LABEL version="2.0"
LABEL description="Triton Inference Server for STAD-AI Version 2"

COPY triton/model_repository /models

EXPOSE 8000 8001 8002

CMD ["tritonserver", "--model-repository=/models", "--disable-auto-complete-config"]
