# ERYNDEX contact API deployment

The public website is hosted on GitHub Pages, which is static hosting and cannot run a server-side form handler. This directory contains a Cloudflare Worker adapter for the contact form. **It is not deployed yet**, and the online form must not be described as live until the deployment and end-to-end test are complete.

## Required configuration

1. Create a Cloudflare Worker from this directory and deploy it.
2. Set Worker variables:
   - `ALLOWED_ORIGINS`: exact comma-separated HTTPS origins, initially `https://arshiataheri851-ops.github.io`; later add the production domain origin.
   - `CONTACT_TO`: the mailbox that should receive inquiries (currently intended: `eryndexco@gmail.com`).
   - `CONTACT_FROM`: a sender address on a domain verified with the email delivery provider.
3. Add `RESEND_API_KEY` as a Worker secret, never as a source-code variable.
4. Configure Cloudflare rate limiting and Turnstile or equivalent abuse protection before public launch. The Worker validates origin, method, content type, body size, field types and lengths, and a honeypot, but those controls alone are not sufficient against automated abuse.
5. Set `window.ERYNDEX_CONTACT_ENDPOINT` in the website to the deployed Worker URL. Do not set it until the Worker has been deployed and tested.
6. Test valid submissions, invalid email, oversized payload, disallowed origin, OPTIONS preflight, provider failure and successful delivery.

## Data handling

The Worker forwards the submitted name, email, optional company, selected service and project brief to the configured mailbox through the email provider. It does not intentionally persist submissions. Keep the privacy notice accurate and establish an appropriate retention policy for the receiving mailbox.

## Security limitations

- GitHub Pages does not let this repository set arbitrary HTTP response headers. The meta CSP on the HTML page is only a partial browser-side control; it is not equivalent to server response headers.
- Before the production domain goes live, configure response headers at the CDN/hosting layer: Content-Security-Policy, Strict-Transport-Security (only after HTTPS is confirmed), X-Content-Type-Options, Referrer-Policy, Permissions-Policy and frame protections.
- Enable provider-side abuse controls, monitoring and alerts. Never place API keys, database credentials or private tokens in frontend JavaScript.
- Do not collect sensitive personal information or confidential project secrets in the public form.
