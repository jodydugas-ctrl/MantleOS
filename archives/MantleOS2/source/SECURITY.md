# Security Policy

## Supported version

Security fixes currently target the `2.0.0-alpha` line.

## Reporting

Please use GitHub's private vulnerability reporting for suspected security
problems. Do not place credentials, private organism state, decrypted VCW data,
or exploit details in a public issue.

## Secret boundary

The repository refuses `.mantle/`, `COMMUNICATION.TXT`, `Food.txt`, private-key
files, and recognized credential shapes. OpenRouter credentials used by the
manual live check are stored only as encrypted GitHub Actions secrets. Live
provider workflows never run for pushes, pull requests, forks, or schedules.

No public receipt is proof that a secret is safe to disclose.

