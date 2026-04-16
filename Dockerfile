ARG SOURCE_REPO=https://github.com/BIOFIN-EU/Risk-Score-Framework
FROM python:3.12
LABEL org.opencontainers.image.source=${SOURCE_REPO}

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV PIP_VERSION_TO_INSTALL="25.0.1"

# install essential OS libs
RUN apt-get update && \
    apt-get install -y \
    wget \
    unzip \
    git \
    cmake \
    pkg-config \
    build-essential \
    libpq-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -U pip==${PIP_VERSION_TO_INSTALL} && \
    rm -rf /tmp/pip* /root/.cache

RUN mkdir /service

# Set the working directory to /service
WORKDIR /service

# only change this layer if requirements change
COPY pyproject.toml /service/pyproject.toml
RUN mkdir -p /service/risk_framework/ && \
    touch /service/risk_framework/__init__.py
RUN pip install -e . && \
    rm -rf /tmp/pip* /root/.cache

#change this layer onwards with any code change
# Copy the current directory contents into the container at /service
COPY . /service

# Add the default cmd script and set the execute permissions (should already be set)
COPY run_server.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/run_server.sh
