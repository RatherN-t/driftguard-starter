# Credential setup

## Mistral

1. Redeem the hackathon credits.
2. Create an API key in the same Mistral workspace.
3. Put it in `.env` as `MISTRAL_API_KEY`.
4. Run:

```bash
python scripts/list_mistral_models.py
```

5. Confirm the configured chat, transcription, and embedding model aliases appear or replace them with accessible aliases.

Never commit the key. Never send it to the browser.

The credential-free demo does not need this key. Add it locally only when analyzing linked live
Google/GitHub evidence, extracting decisions from a custom transcript, uploading audio to Voxtral,
or using Mistral/Codestral embeddings. You do not need to send the key to Codex.

## Google Drive and Docs

1. Create or select a [Google Cloud project](https://console.cloud.google.com/projectcreate).
2. Enable the [Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)
   and [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
   in that same project.
3. Open [IAM service accounts](https://console.cloud.google.com/iam-admin/serviceaccounts),
   create a service account such as `driftguard-local`, and do not grant broad project roles.
4. Open that account, choose **Keys > Add key > Create new key > JSON**, and download the
   one-time JSON credential.
5. Move it to `secrets/google-service-account.json`. This directory is gitignored. Never paste,
   print, email, or commit this file.
6. Copy the service-account email from the Cloud console. Create a disposable Drive folder and
   Google Doc, click **Share**, add that email, turn off notification, and grant **Viewer** for the
   first read test or **Editor** for the later approved-write test. No domain-wide delegation or
   Workspace administrator role is needed.
7. Copy the folder ID from the characters after `/folders/` in its Drive URL.
8. Configure the local `.env` without sending the values to another person:

```dotenv
DEMO_MODE=false
GOOGLE_SERVICE_ACCOUNT_FILE=./secrets/google-service-account.json
GOOGLE_DRIVE_FOLDER_ID=<folder-id-from-the-drive-url>
GOOGLE_WRITE_ENABLED=false
```

9. Restart the backend. Confirm `/api/config/status` reports `google_read_ready: true`, then test
   the direct Google Docs share URL in the source setup screen.
10. Only after the read test passes, give the service account **Editor** access and change
    `GOOGLE_WRITE_ENABLED=true`. Keep the document disposable: applying a patch is a real write,
    although DriftGuard still requires separate approve and apply actions and checks the revision.

The source setup screen accepts a direct Google Docs share URL. Share that document (or its parent
folder) with the service-account email before building the alignment view.

The folder ID is the segment after `/folders/` in the Drive URL.

## GitHub

Fastest path: use a public demo repository and no token.

For a private repository, open [GitHub fine-grained token settings](https://github.com/settings/personal-access-tokens/new):

1. Name it `DriftGuard local UAT`, give it a short expiration, and select the repository owner.
2. Select **Only select repositories** and choose only the disposable test repository.
3. Under repository permissions, grant **Contents: Read-only** and **Pull requests: Read-only**.
   Metadata read access is included automatically. Do not grant write permissions.
4. Generate and copy the token once, then put it directly in the local `.env` as
   `GITHUB_TOKEN=<fine-grained-token>`. Never paste it into chat or commit it.
5. Restart the backend and confirm `/api/config/status` reports `github_authenticated: true`.

The UI requires canonical matching URLs:

```text
https://github.com/<owner>/<repository>
https://github.com/<owner>/<repository>/pull/<positive-number>
```

The PR must contain no more than `GITHUB_MAX_CHANGED_FILES` (10 by default), and each full changed
file must be no more than `GITHUB_MAX_FILE_BYTES` (100,000 by default).

Do not grant write access for the MVP.

## Email

Start with:

```text
EMAIL_MODE=console
```

The app should render or print the exact email rather than sending it.

After the full demo works, configure SMTP and switch to `EMAIL_MODE=smtp`. Keep code excerpts out of email by default.
