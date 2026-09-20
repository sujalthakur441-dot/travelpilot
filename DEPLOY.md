# Deploying TravelPilot (get a live link + credentials for judges)

I can't push this to a live host directly from here (this build
environment has no internet access and no hosting credentials of
yours) — but everything's pre-configured so this should take you
under 10 minutes on Render's free tier.

## Option A — Render.com (recommended, free tier, no CLI needed)

1. Push this `travelpilot/` folder to a **GitHub repo** (can be private).
2. Go to [render.com](https://render.com) → sign in with GitHub.
3. **New +** → **Web Service** → pick your repo.
4. Render should auto-detect `render.yaml` and pre-fill the build/start
   commands. If not, set manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment**, add:
   - `ANTHROPIC_API_KEY` — your Claude key (enables real AI reasoning)
   - `GOOGLE_PLACES_API_KEY` — optional, enables live place data
   - `DASHBOARD_USERNAME` — pick something simple, e.g. `judge`
   - `DASHBOARD_PASSWORD` — pick a password, e.g. a short random string
6. Click **Deploy**. First deploy takes ~2–3 minutes.
7. You'll get a URL like `https://travelpilot-xxxx.onrender.com`.
   That's the link to hand judges, along with the username/password
   you set in step 5 (they'll see a browser login popup).

**Free tier note:** Render's free web services sleep after ~15 min of
inactivity and take ~30–50 seconds to wake up on the next request.
If judges are testing it live and timing matters, either:
- open the link yourself a minute before they test, or
- upgrade to a paid instance for the day, or
- use Railway instead (Option B), which has a similar free tier
  with less aggressive sleep behavior.

## Option B — Railway.app

Same idea, slightly different UI:
1. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo.
2. Railway reads the `Dockerfile` automatically.
3. Add the same 4 environment variables as above under **Variables**.
4. Deploy → Railway gives you a public URL under **Settings → Networking → Generate Domain**.

## Option C — Fly.io

If you prefer the CLI and already have `flyctl` installed:
```bash
fly launch          # detects the Dockerfile, follow the prompts
fly secrets set ANTHROPIC_API_KEY=... GOOGLE_PLACES_API_KEY=... DASHBOARD_USERNAME=... DASHBOARD_PASSWORD=...
fly deploy
```

## Testing before you send the link to judges

1. Open the live URL — you should get a login popup (if you set
   `DASHBOARD_USERNAME`/`PASSWORD`). Log in.
2. Check the two status badges top-right of the dashboard — confirm
   they say "Claude reasoning active" and/or "Live Google Places
   data" if you configured those keys.
3. Run through the full demo flow once yourself end-to-end (build →
   autopilot or manual disruption → ask a question) before sharing
   the link, so you know the free-tier server is awake and warmed up.

## What to send judges

- The live URL
- The username and password you set
- Optionally, point them at `README.md` in the repo for the "how it
  works" explanation, since they'll be testing it more than once.
