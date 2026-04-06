#!/bin/bash

uv run uvicorn project_manager_agent.web.app:create_app --factory --reload