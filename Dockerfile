# syntax=docker/dockerfile:1.4

### Builder stage ----------------------------------------------------------
FROM python:3.10-slim AS builder

ENV VIRTUAL_ENV=/opt/venv \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for isolated install
RUN python -m venv ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /app

# Pre-install project dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source and install it into the venv
COPY . .
RUN pip install --no-cache-dir .

### Runtime stage ----------------------------------------------------------
FROM python:3.10-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH="${VIRTUAL_ENV}/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    WEIBO_COOKIES_PATH=/app/cookies/weibo_cookies.json

# Copy the virtual environment with the installed application
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

WORKDIR /app

# Copy runtime assets (entrypoint, default project files)
COPY docker/entrypoint.sh /entrypoint.sh
COPY . /app

# Install Chrome/Chromedriver and other OS dependencies required by Selenium
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        xvfb \
        x11vnc \
        fluxbox \
        tzdata \
        fonts-noto-cjk \
        fonts-noto-color-emoji \
        libnss3 \
        libgconf-2-4 \
        libxss1 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libgbm1 \
        libasound2 \
        libxrandr2 \
        libxcomposite1 \
        libxcursor1 \
        libxi6 \
        libxdamage1 \
        libxtst6 \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Prepare persistent directories and entrypoint permissions
RUN mkdir -p /app/data /app/logs /app/chroma_db /app/cookies \
    && chmod +x /entrypoint.sh

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["python", "-m", "chatbot.main", "--monitor"]
