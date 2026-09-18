# GridWise submission

**Live API:** https://gridwise-production-0e08.up.railway.app
**GitHub repository:** https://github.com/abdullahalyf/bup-hackathon-preli
**Container image:** `ghcr.io/abdullahalyf/gridwise:v1`
**Video link:** TBD

## Endpoints

- `GET /health` — health check.
- `POST /optimize-energy` — submit the 24-hour request described in [CONTRACTS.md](CONTRACTS.md).
- `GET /` — frontend if present in the deployed version.

## Docker

```sh
docker pull ghcr.io/abdullahalyf/gridwise:v1
docker run --rm -p 8000:8000 --env-file .env ghcr.io/abdullahalyf/gridwise:v1
```

Create a local `.env` file with only the provider variables you use. Never commit it. The container listens on port 8000. Check `http://localhost:8000/health`.

## Environment variable names

`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_MODEL`, `PORT`.

## Final rubric checklist

- [x] Live base URL responds to `/health` and `/optimize-energy` from outside the development machine.
- [ ] GitHub repository link is accessible as required by the submission rules.
- [ ] Exact Docker image tag pulls and runs; `/health` responds from the container.
- [x] README covers quickstart, environment variable names, model/provider, architecture, API example, sample tests, Docker, and limitations.
- [x] Public samples: 10/10 interpretation and cost within 0.01 BDT; replay check has no violations.
- [ ] Paraphrase check accuracy is at least 90%.
- [x] API tests pass with `python -m pytest -q`.
- [ ] Demo video is at most three minutes and its link is publicly viewable.
- [x] Repository and deployment contain no secrets.
