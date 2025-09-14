# 1. Base image
FROM python:3.12-slim-bullseye

# 2. 시스템 라이브러리 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 소스 코드 복사 및 의존성 설치
COPY pyproject.toml ./
COPY . .
RUN pip install --upgrade pip setuptools wheel \
    && pip install .

# 5. 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 6. 포트 노출
EXPOSE 8501

# 7. 실행 명령
CMD streamlit run ./interface/streamlit_app.py --server.port=8501
