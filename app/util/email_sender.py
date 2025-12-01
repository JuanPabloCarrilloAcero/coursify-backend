import logging
import os
from typing import Optional, Tuple

import resend

LOGGER = logging.getLogger(__name__)


def _ensure_client() -> Tuple[str, str, str]:
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not configured")

    resend.api_key = api_key

    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    from_name = os.getenv("RESEND_FROM_NAME", "Cousify")
    return api_key, from_email, from_name


def send_password_reset_email(to_email: str, code: str, *, ttl_minutes: int = 10,
                              locale_label: Optional[str] = None) -> None:
    """Dispatch the verification code using Resend."""
    _, from_email, from_name = _ensure_client()
    support_email = os.getenv("SUPPORT_EMAIL", from_email)
    intro = locale_label or "Código para restablecer tu contraseña"
    subject = f"{from_name} — {intro}"

    html = f"""
    <!doctype html>
    <html>
      <body style="font-family: Arial, Helvetica, sans-serif; color: #111; line-height: 1.4; background: #f6f7fb; padding: 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
          <tr>
            <td align="center">
              <table width="600" style="max-width:600px;">
                <tr>
                  <td style="background: #ffffff; padding: 28px; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h2 style="margin:0 0 12px 0; color:#0b2a3a;">{intro}</h2>
                    <p style="margin:0 0 18px 0; color:#334454;">
                      Solicitud recibida para restablecer la contraseña de tu cuenta en <strong>{from_name}</strong>. Utiliza el siguiente código para continuar:
                    </p>

                    <div style="display:inline-block; margin:18px 0; padding:14px 22px; background:#f3f6f9; border-radius:8px; border:1px solid #e1e8ee; font-family:monospace; font-size:22px; letter-spacing:6px; font-weight:700; color:#0b2a3a;">
                      {code}
                    </div>

                    <p style="margin:16px 0 0; color:#6b7b86;">
                      Este código caduca en {ttl_minutes} minutos.
                    </p>

                    <hr style="border:none; border-top:1px solid #eef1f4; margin:20px 0;">

                    <p style="margin:0; color:#6b7b86; font-size:14px;">
                      Si no solicitaste este cambio, puedes ignorar este correo o ponerte en contacto con nuestro equipo de soporte: <a href="mailto:{support_email}" style="color:#0b66c2;">{support_email}</a>.
                    </p>

                    <p style="margin:16px 0 0; color:#6b7b86; font-size:14px;">
                      No compartas este código con nadie. <br>Atentamente,<br>El equipo de {from_name}
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding-top:12px; text-align:center; color:#98a6b0; font-size:12px;">
                    {from_name} — Si tienes problemas, responde a este correo o visita nuestro centro de ayuda.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    text = f"""{intro}

Solicitaste restablecer tu contraseña en {from_name}. Usa este código:

{code}

Caduca en {ttl_minutes} minutos.

Si no solicitaste este cambio, ignora este correo o contacta a soporte: {support_email}

No compartas este código con nadie.

Atentamente,
El equipo de {from_name}
"""

    try:
        resend.Emails.send({
            "from": f"{from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
            "text": text,
        })
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Failed to send reset code with Resend: %s", exc)
        raise
