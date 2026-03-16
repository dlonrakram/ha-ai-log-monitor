ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy application code
COPY app/ /app/

# Copy rootfs overlay (s6-overlay service definitions)
COPY rootfs/ /

# Ensure service scripts are executable (Git may strip permissions)
RUN chmod a+x /etc/services.d/ai_log_monitor/run \
    && chmod a+x /etc/services.d/ai_log_monitor/finish
