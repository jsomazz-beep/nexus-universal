from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger(__name__)


def send_report_email(
    email_cfg: dict,
    env: dict[str, str],
    html_body: str,
    text_body: str,
    html_attachment_path: str | None,
    retries: int = 2,
    backoff_seconds: int = 2,
) -> None:
    smtp_host = env.get("SMTP_HOST")
    smtp_port = int(env.get("SMTP_PORT", "587"))
    smtp_user = env.get("SMTP_USERNAME")
    smtp_pass = env.get("SMTP_PASSWORD")
    use_tls = env.get("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not smtp_user or not smtp_pass:
        raise RuntimeError("Credenciais SMTP incompletas no .env")

    sender = email_cfg.get("sender", smtp_user)
    recipients = email_cfg.get("recipients", [])
    subject = email_cfg.get("subject", "Relatório semanal")
    fmt = email_cfg.get("delivery_format", "html_body_plus_html_attachment")

    if not recipients:
        raise RuntimeError("Lista de destinatários vazia em config.email.recipients")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if fmt in {"html_body_plus_html_attachment", "html_attachment_only"} and html_attachment_path:
        attachment_path = Path(html_attachment_path)
        if attachment_path.exists():
            message.add_attachment(
                attachment_path.read_bytes(),
                maintype="text",
                subtype="html",
                filename=attachment_path.name,
            )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(message)
            logger.info("E-mail enviado com sucesso para %s", recipients)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.error("Falha no envio de e-mail (tentativa %s): %s", attempt + 1, exc)
            if attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))

    raise RuntimeError(f"Não foi possível enviar e-mail após retries: {last_error}")
