FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server python3 python3-pip \
        iproute2 iputils-ping nmap sshpass && \
    pip install cryptography --break-system-packages --quiet && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    mkdir /var/run/sshd && \
    echo 'root:hospital123' | chpasswd && \
    sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    useradd -m -s /bin/bash ehradmin && \
    echo 'ehradmin:Hospital2024!' | chpasswd

COPY trimmed_data/ehr_data/ /opt/ehr_data/
COPY trimmed_data/iot_data/ /opt/iot_data/
COPY trimmed_data/portal_data/ /opt/portal_data/

COPY setup_data.sh /opt/setup_data.sh
RUN chmod +x /opt/setup_data.sh

EXPOSE 22

CMD ["/bin/bash", "-c", "/opt/setup_data.sh && /usr/sbin/sshd -D"]
