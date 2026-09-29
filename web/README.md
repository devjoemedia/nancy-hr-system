# HR System – Web Version

Putting the HR system online for free on PythonAnywhere.

---

# Deployment steps

This folder (`web/`) is the HR system as a website, behind a login. It is
a standalone project: everything it needs is inside this folder. These steps host it free on **PythonAnywhere**. Your site will be at:

    https://YOUR-USERNAME.pythonanywhere.com

It takes about 15 minutes. Wherever you see `YOUR-USERNAME`, use your
PythonAnywhere username.

> **This site holds personal data** (Ghana Card and SSNIT numbers, salaries).
> Only give logins to people who should see all staff records, use strong
> passwords, and keep regular backups (step 8).

---

## 1. Create a free account

Go to https://www.pythonanywhere.com, choose **Pricing & signup → Create a
Beginner account** (free). Your username becomes part of the web address.

## 2. Copy the code onto PythonAnywhere

Open **Consoles → Bash** and run:

```bash
git clone https://github.com/devjoemedia/nancy-hr-system.git
cd nancy-hr-system/web
```

If the GitHub repository is **private**, create a token on GitHub
(**Settings → Developer settings → Personal access tokens → Fine-grained**,
read-only access to this repository) and clone with:

```bash
git clone https://YOUR-GITHUB-NAME:YOUR-TOKEN@github.com/devjoemedia/nancy-hr-system.git
cd nancy-hr-system/web
```

## 3. Install what it needs

Still in the Bash console:

```bash
mkvirtualenv hrweb --python=python3.10
pip install -r requirements.txt
```

(Your prompt now starts with `(hrweb)`. If you open a new console later, run
`workon hrweb` first.)

## 4. Create the first login

```bash
flask --app app create-user
```

Type a username and a password of at least 8 characters. You can add more
users from the website's **Users** page afterwards.

**Bringing over existing data (optional):** to start with the records from the
desktop app, open the **Files** tab, go to `/home/YOUR-USERNAME/nancy-hr-system/web/`
and upload your `hr_management.db` (and the contents of your `photos` folder
into a `photos` folder there) **before** running `create-user`.

## 5. Create the web app

1. Open the **Web** tab → **Add a new web app** → **Next**.
2. Choose **Manual configuration** (not Flask) → **Python 3.10** → **Next**.
3. In the **Virtualenv** section, enter:

   ```
   /home/YOUR-USERNAME/.virtualenvs/hrweb
   ```

4. In the **Code** section, click the **WSGI configuration file** link, delete
   everything in it, paste the following, then click **Save**:

   ```python
   import sys

   path = "/home/YOUR-USERNAME/nancy-hr-system/web"
   if path not in sys.path:
       sys.path.insert(0, path)

   from app import app as application
   ```

5. In the **Static files** section, add:

   | URL | Directory |
   |---|---|
   | `/static/` | `/home/YOUR-USERNAME/nancy-hr-system/web/static` |

6. In the **Security** section, switch **Force HTTPS** on. (Required: sign-in
   only works over HTTPS.)

## 6. Start it

Click the green **Reload** button at the top of the Web tab, then open
`https://YOUR-USERNAME.pythonanywhere.com` and sign in.

## 7. Updating after changes

When new code is pushed to GitHub:

```bash
cd ~/nancy-hr-system/web
git pull
workon hrweb
pip install -r requirements.txt
```

Then click **Reload** on the Web tab. Your data is not touched.

## 8. Backups

**Quick copy for reading:** the **Export to Excel** button on the Dashboard
or Reports page downloads every record as a spreadsheet. That's handy for
viewing and sharing, but it can't be loaded back in, so also keep the
backups below.

Everything lives in two places inside `/home/YOUR-USERNAME/nancy-hr-system/web/`:

- `hr_management.db` — all records and logins
- `photos/` — employee pictures

Download them regularly from the **Files** tab (for the photos folder, run
`zip -r photos.zip photos` in a Bash console first, then download the zip).

---

## Free plan limits

- **Keep it switched on:** free sites stop after 3 months unless you log in
  and click **"Run until 3 months from today"** on the Web tab. PythonAnywhere
  emails you a reminder.
- **Size:** 512 MB of storage, which is plenty for this system.
- **Web address:** always `YOUR-USERNAME.pythonanywhere.com` (a custom domain
  needs a paid plan).
- **Speed:** fine for a small HR team; not meant for heavy traffic.

## If something goes wrong

- **"Something went wrong" / error page:** Web tab → **Error log** (bottom of
  the page) shows the reason.
- **Sign-in page keeps saying the form expired:** make sure **Force HTTPS**
  is on and you're using the `https://` address.
- **Forgot a password:** in a Bash console, `cd ~/nancy-hr-system/web`,
  `workon hrweb`, then `flask --app app create-user` to make a new login,
  sign in with it, and remove the old one on the **Users** page.

---

## Running the web version on your own computer

From inside this `web` folder:

```bash
pip install -r requirements.txt
flask --app app create-user
flask --app app run --debug
```

Then open http://127.0.0.1:5000. Records are kept in `web/hr_management.db`,
separate from the desktop app's. (`--debug` is for testing on your own
computer only.)

To start the website with the desktop app's existing records, copy
`desktop/hr_management.db` (and `desktop/photos/`) into this folder first.
