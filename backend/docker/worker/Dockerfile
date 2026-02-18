ARG BASE_IMAGE=evmbench/base:latest
FROM ${BASE_IMAGE}

RUN python3 -m pip install --no-cache-dir httpx uvloop loguru
COPY docker/worker/init.py /tmp/init.py
COPY worker_runner/ /opt/evmbench/worker_runner/
RUN chmod +x /opt/evmbench/worker_runner/run_codex_detect.sh

CMD ["python3", "/tmp/init.py"]
