FROM jenkins/jenkins:lts
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip curl \
    && curl -fsSL https://get.docker.com | sh \
    && rm -rf /var/lib/apt/lists/*
RUN usermod -aG docker jenkins
USER jenkins