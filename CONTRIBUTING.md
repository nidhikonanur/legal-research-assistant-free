# Contributing

Thanks for contributing to `legal-research-assistant-free`.

## Local Setup

1. Copy `.env.example` to `.env`
2. Create a Python virtual environment
3. Install backend dependencies from `server/requirements.txt`
4. Install frontend dependencies from `client/package.json`
5. Run the backend and frontend in separate terminals

## Suggested Workflow

1. Create a branch for your change
2. Keep changes focused and easy to review
3. Update documentation when behavior changes
4. Prefer small commits with clear messages

## Good First Improvements

- add tests for the backend search pipeline
- improve UI formatting for citations and summaries
- make CourtListener parsing more robust
- add error states and loading polish in the client

## Before Opening a PR

- verify the backend starts
- verify the frontend starts
- confirm `.env`, virtualenvs, and local vector data are not committed
