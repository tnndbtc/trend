# AI Trend Intelligence Platform - Admin Interface Architecture

**Document Type:** System Design Document
**Status:** Production-Grade Specification
**Last Updated:** 2026-02-10
**Architecture Version:** 1.0

---

## Executive Summary

This document specifies the production architecture for the Administrative Interface that enables platform operators to manage critical system parameters, prompts, configurations, agents, and data. The admin interface provides centralized control over the AI Trend Intelligence Platform while maintaining security, auditability, and operational safety.

**Key Design Principles:**
- **Version Control Everything:** Prompts, configs, and schemas are versioned like code
- **Hot-Reload Capable:** Changes apply without system restarts
- **Audit Trail:** Complete history of who changed what and when
- **Approval Workflows:** Critical changes require multi-party approval
- **Rollback-Ready:** All changes can be instantly reverted
- **Developer-Friendly:** Configuration as code with UI overlay

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Admin Backend Architecture](#2-admin-backend-architecture)
3. [Prompt Management System](#3-prompt-management-system)
4. [Configuration Management](#4-configuration-management)
5. [Agent Control Plane Administration](#5-agent-control-plane-administration)
6. [Data Management Interface](#6-data-management-interface)
7. [User & Access Control](#7-user--access-control)
8. [Admin UI Architecture](#8-admin-ui-architecture)
9. [Security & Audit](#9-security--audit)
10. [Operations & Deployment](#10-operations--deployment)

---

## 1. System Overview

### 1.1 Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      Admin Web UI (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Prompt Editor │  │Config Manager│  │Agent Dashboard       │  │
│  │Data Curator  │  │User Manager  │  │Monitoring Console    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │ HTTPS/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                    Admin API Gateway (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Auth & RBAC   │  │Rate Limiting │  │Audit Logging         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│                    Admin Service Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Prompt Mgmt   │  │Config Mgmt   │  │Agent Control Admin   │  │
│  │Data Curation │  │User Mgmt     │  │Change Management     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────────┐
│                    Storage Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │PostgreSQL    │  │Redis Cache   │  │Git Repository        │  │
│  │(Admin data)  │  │(Hot config)  │  │(Version control)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Capabilities

**Prompt Management:**
- Version-controlled prompt library
- A/B testing framework
- Performance tracking per prompt version
- Template inheritance and composition

**Configuration Management:**
- Hierarchical configuration (system → category → source)
- Hot-reload without restarts
- Environment-specific configs (dev, staging, prod)
- Config validation and rollback

**Agent Administration:**
- Budget and quota management
- Trust level configuration
- Task arbitration rules
- Circuit breaker settings

**Data Curation:**
- Bulk operations (merge, delete, archive)
- Manual trend editing
- Content moderation
- Source management

**Access Control:**
- Role-based permissions
- API key lifecycle management
- Multi-factor authentication
- Session management

---

## 2. Admin Backend Architecture

### 2.1 Admin API Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Admin API (FastAPI)                           │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Authentication Middleware                   │    │
│  │  - JWT token validation                                  │    │
│  │  - Role-based access control (RBAC)                      │    │
│  │  - Admin-only routes protection                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Admin Router Layer                      │    │
│  │  /admin/prompts/*    /admin/config/*                     │    │
│  │  /admin/agents/*     /admin/data/*                       │    │
│  │  /admin/users/*      /admin/audit/*                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Change Management Layer                     │    │
│  │  - Change request creation                               │    │
│  │  - Approval workflow engine                              │    │
│  │  - Rollback mechanism                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Admin API Endpoints

```python
# ============================================================
# PROMPT MANAGEMENT
# ============================================================

# Prompt Library
GET    /admin/prompts                      # List all prompts
GET    /admin/prompts/{id}                 # Get prompt details
POST   /admin/prompts                      # Create new prompt
PUT    /admin/prompts/{id}                 # Update prompt
DELETE /admin/prompts/{id}                 # Archive prompt

# Prompt Versions
GET    /admin/prompts/{id}/versions        # List versions
GET    /admin/prompts/{id}/versions/{v}    # Get specific version
POST   /admin/prompts/{id}/versions        # Create new version
POST   /admin/prompts/{id}/rollback/{v}    # Rollback to version

# Prompt Testing
POST   /admin/prompts/{id}/test            # Test prompt with sample data
GET    /admin/prompts/{id}/performance     # Get performance metrics
POST   /admin/prompts/{id}/ab-test         # Start A/B test

# ============================================================
# CONFIGURATION MANAGEMENT
# ============================================================

# Configuration
GET    /admin/config                       # Get all configs
GET    /admin/config/{key}                 # Get specific config
PUT    /admin/config/{key}                 # Update config
POST   /admin/config/reload                # Hot-reload configs
POST   /admin/config/validate              # Validate config changes

# Configuration History
GET    /admin/config/history               # Config change history
POST   /admin/config/rollback/{id}         # Rollback to previous config

# ============================================================
# AGENT CONTROL PLANE ADMINISTRATION
# ============================================================

# Agent Management
GET    /admin/agents                       # List all agents
GET    /admin/agents/{id}                  # Get agent details
PUT    /admin/agents/{id}/budget           # Update budget
PUT    /admin/agents/{id}/trust-level      # Update trust level
POST   /admin/agents/{id}/suspend          # Suspend agent
POST   /admin/agents/{id}/activate         # Activate agent

# Task Management
GET    /admin/tasks                        # List all tasks
GET    /admin/tasks/{id}                   # Get task details
POST   /admin/tasks/{id}/cancel            # Cancel running task
POST   /admin/tasks/{id}/retry             # Retry failed task

# Circuit Breaker Management
GET    /admin/circuit-breakers             # List tripped breakers
POST   /admin/circuit-breakers/{id}/reset  # Reset circuit breaker
GET    /admin/circuit-breakers/{id}/graph  # Get causality graph

# ============================================================
# DATA MANAGEMENT
# ============================================================

# Trend Curation
GET    /admin/trends                       # List trends (with filters)
PUT    /admin/trends/{id}                  # Edit trend manually
DELETE /admin/trends/{id}                  # Delete trend
POST   /admin/trends/merge                 # Merge duplicate trends
POST   /admin/trends/bulk-delete           # Bulk delete

# Source Management
GET    /admin/sources                      # List data sources
POST   /admin/sources                      # Add new source
PUT    /admin/sources/{id}                 # Update source config
POST   /admin/sources/{id}/test            # Test source connection
DELETE /admin/sources/{id}                 # Remove source

# Content Moderation
GET    /admin/moderation/queue             # Get moderation queue
POST   /admin/moderation/{id}/approve      # Approve content
POST   /admin/moderation/{id}/reject       # Reject content
POST   /admin/moderation/{id}/flag         # Flag for review

# ============================================================
# USER & ACCESS MANAGEMENT
# ============================================================

# User Management
GET    /admin/users                        # List users
POST   /admin/users                        # Create user
PUT    /admin/users/{id}                   # Update user
DELETE /admin/users/{id}                   # Deactivate user
POST   /admin/users/{id}/reset-password    # Force password reset

# Role Management
GET    /admin/roles                        # List roles
POST   /admin/roles                        # Create role
PUT    /admin/roles/{id}                   # Update role permissions

# API Key Management
GET    /admin/api-keys                     # List API keys
POST   /admin/api-keys                     # Generate new key
DELETE /admin/api-keys/{id}                # Revoke key
GET    /admin/api-keys/{id}/usage          # Get usage statistics

# ============================================================
# AUDIT & MONITORING
# ============================================================

# Audit Logs
GET    /admin/audit                        # Query audit logs
GET    /admin/audit/{id}                   # Get specific audit entry
POST   /admin/audit/export                 # Export audit logs

# System Health
GET    /admin/health                       # System health status
GET    /admin/metrics                      # Key platform metrics
GET    /admin/alerts                       # Active alerts

# Change Requests
GET    /admin/changes                      # List pending changes
POST   /admin/changes/{id}/approve         # Approve change
POST   /admin/changes/{id}/reject          # Reject change
```

### 2.3 Admin API Implementation

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================
# RBAC Dependency
# ============================================================

async def require_admin(current_user = Depends(get_current_user)):
    """Require admin role for all admin endpoints"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_permission(permission: str):
    """Require specific permission"""
    async def _check(current_user = Depends(get_current_user)):
        if not await has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user
    return _check


# ============================================================
# PROMPT MANAGEMENT ENDPOINTS
# ============================================================

@router.get("/prompts")
async def list_prompts(
    category: Optional[str] = None,
    admin_user = Depends(require_admin)
):
    """List all prompts in the system"""
    prompts = await prompt_service.list_prompts(category=category)
    return {"prompts": prompts}


@router.post("/prompts")
async def create_prompt(
    request: CreatePromptRequest,
    admin_user = Depends(require_permission("prompts.create"))
):
    """Create new prompt template"""

    # Validate prompt template
    validation = await prompt_service.validate_template(
        template=request.template,
        variables=request.variables
    )

    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid prompt template: {validation.error}"
        )

    # Create prompt
    prompt = await prompt_service.create_prompt(
        name=request.name,
        description=request.description,
        template=request.template,
        variables=request.variables,
        category=request.category,
        created_by=admin_user.id
    )

    # Log change
    await audit_log.log_change(
        user_id=admin_user.id,
        action="prompt.created",
        resource_type="prompt",
        resource_id=prompt.id,
        changes={"name": request.name}
    )

    return {"prompt": prompt}


@router.put("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    request: UpdatePromptRequest,
    admin_user = Depends(require_permission("prompts.update"))
):
    """Update prompt template (creates new version)"""

    # Get existing prompt
    existing = await prompt_service.get_prompt(prompt_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prompt not found")

    # Create new version
    new_version = await prompt_service.create_version(
        prompt_id=prompt_id,
        template=request.template,
        variables=request.variables,
        change_description=request.change_description,
        created_by=admin_user.id
    )

    # Log change
    await audit_log.log_change(
        user_id=admin_user.id,
        action="prompt.updated",
        resource_type="prompt",
        resource_id=prompt_id,
        changes={
            "version": new_version.version_number,
            "description": request.change_description
        }
    )

    return {"version": new_version}


@router.post("/prompts/{prompt_id}/test")
async def test_prompt(
    prompt_id: int,
    request: TestPromptRequest,
    admin_user = Depends(require_admin)
):
    """Test prompt with sample data"""

    prompt = await prompt_service.get_prompt(prompt_id)

    # Render template with test data
    rendered = await prompt_service.render_template(
        template=prompt.template,
        variables=request.test_data
    )

    # Execute with LLM
    result = await llm_service.complete(
        prompt=rendered,
        max_tokens=request.max_tokens or 500,
        temperature=request.temperature or 0.7
    )

    return {
        "rendered_prompt": rendered,
        "llm_response": result.text,
        "tokens_used": result.usage.total_tokens,
        "cost_usd": result.usage.total_tokens * 0.00002  # Example pricing
    }


@router.post("/prompts/{prompt_id}/ab-test")
async def start_ab_test(
    prompt_id: int,
    request: ABTestRequest,
    admin_user = Depends(require_permission("prompts.ab-test"))
):
    """Start A/B test between prompt versions"""

    # Validate versions exist
    version_a = await prompt_service.get_version(prompt_id, request.version_a)
    version_b = await prompt_service.get_version(prompt_id, request.version_b)

    if not version_a or not version_b:
        raise HTTPException(status_code=400, detail="Invalid versions")

    # Create A/B test
    ab_test = await ab_test_service.create_test(
        prompt_id=prompt_id,
        version_a=request.version_a,
        version_b=request.version_b,
        traffic_split=request.traffic_split or 0.5,
        sample_size=request.sample_size or 1000,
        success_metric=request.success_metric,
        created_by=admin_user.id
    )

    return {"ab_test": ab_test}


# ============================================================
# CONFIGURATION MANAGEMENT ENDPOINTS
# ============================================================

@router.get("/config")
async def get_all_configs(
    admin_user = Depends(require_admin)
):
    """Get all configuration values"""
    configs = await config_service.get_all_configs()
    return {"configs": configs}


@router.put("/config/{key}")
async def update_config(
    key: str,
    request: UpdateConfigRequest,
    admin_user = Depends(require_permission("config.update"))
):
    """Update configuration value"""

    # Validate config value
    validation = await config_service.validate_config(
        key=key,
        value=request.value
    )

    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid config value: {validation.error}"
        )

    # Check if critical config (requires approval)
    config_def = await config_service.get_config_definition(key)

    if config_def.requires_approval:
        # Create change request
        change = await change_management.create_change_request(
            change_type="config.update",
            resource_key=key,
            old_value=await config_service.get_config(key),
            new_value=request.value,
            justification=request.justification,
            requested_by=admin_user.id
        )

        return {
            "status": "pending_approval",
            "change_request_id": change.id,
            "message": "Change requires approval"
        }

    # Apply change immediately
    await config_service.update_config(
        key=key,
        value=request.value,
        updated_by=admin_user.id
    )

    # Trigger hot-reload
    await config_service.reload_config(key)

    # Log change
    await audit_log.log_change(
        user_id=admin_user.id,
        action="config.updated",
        resource_type="config",
        resource_id=key,
        changes={"value": request.value}
    )

    return {
        "status": "applied",
        "key": key,
        "value": request.value
    }


@router.post("/config/reload")
async def reload_configs(
    admin_user = Depends(require_permission("config.reload"))
):
    """Hot-reload all configurations"""

    await config_service.reload_all_configs()

    # Notify all services
    await event_bus.publish(
        "config.reloaded",
        {"reloaded_at": datetime.utcnow().isoformat()}
    )

    return {"status": "reloaded"}


# ============================================================
# AGENT ADMINISTRATION ENDPOINTS
# ============================================================

@router.get("/agents")
async def list_agents(
    status: Optional[str] = None,
    admin_user = Depends(require_admin)
):
    """List all agents"""
    agents = await agent_registry.list_agents(status=status)
    return {"agents": agents}


@router.put("/agents/{agent_id}/budget")
async def update_agent_budget(
    agent_id: str,
    request: UpdateBudgetRequest,
    admin_user = Depends(require_permission("agents.update-budget"))
):
    """Update agent budget limits"""

    # Validate budget values
    if request.daily_cost_limit_usd < 0:
        raise HTTPException(status_code=400, detail="Invalid budget value")

    # Update budget
    await agent_control_plane.budget_engine.update_budget(
        agent_id=agent_id,
        daily_cost_limit_usd=request.daily_cost_limit_usd,
        monthly_cost_limit_usd=request.monthly_cost_limit_usd,
        daily_token_quota=request.daily_token_quota,
        max_concurrent_tasks=request.max_concurrent_tasks
    )

    # Log change
    await audit_log.log_change(
        user_id=admin_user.id,
        action="agent.budget_updated",
        resource_type="agent",
        resource_id=agent_id,
        changes=request.dict()
    )

    return {"status": "updated"}


@router.post("/circuit-breakers/{correlation_id}/reset")
async def reset_circuit_breaker(
    correlation_id: str,
    request: ResetCircuitBreakerRequest,
    admin_user = Depends(require_permission("agents.circuit-breaker"))
):
    """Manually reset tripped circuit breaker"""

    # Verify circuit is tripped
    if not await circuit_breaker.is_tripped(correlation_id):
        raise HTTPException(
            status_code=400,
            detail="Circuit breaker is not tripped"
        )

    # Get causality graph for audit
    graph = await lineage_tracker.build_lineage_graph(correlation_id)

    # Reset circuit breaker
    await circuit_breaker.manual_reset(
        correlation_id=correlation_id,
        reset_by=admin_user.id,
        reason=request.reason
    )

    # Log action
    await audit_log.log_change(
        user_id=admin_user.id,
        action="circuit_breaker.reset",
        resource_type="circuit_breaker",
        resource_id=correlation_id,
        changes={
            "reason": request.reason,
            "graph_size": len(graph.edges)
        }
    )

    return {"status": "reset"}


# ============================================================
# DATA MANAGEMENT ENDPOINTS
# ============================================================

@router.post("/trends/merge")
async def merge_trends(
    request: MergeTrendsRequest,
    admin_user = Depends(require_permission("data.merge-trends"))
):
    """Merge duplicate trends"""

    if len(request.trend_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 trends required for merge"
        )

    # Merge trends
    merged = await data_service.merge_trends(
        trend_ids=request.trend_ids,
        primary_trend_id=request.primary_trend_id,
        merge_strategy=request.merge_strategy,
        merged_by=admin_user.id
    )

    # Log action
    await audit_log.log_change(
        user_id=admin_user.id,
        action="trends.merged",
        resource_type="trend",
        resource_id=merged.id,
        changes={
            "merged_ids": request.trend_ids,
            "strategy": request.merge_strategy
        }
    )

    return {"merged_trend": merged}
```

---

## 3. Prompt Management System

### 3.1 Prompt Database Schema

```sql
-- ============================================================
-- PROMPT TEMPLATES
-- ============================================================

CREATE TABLE prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    category VARCHAR(100) NOT NULL,  -- 'summarization', 'classification', 'analysis'

    -- Current active version
    active_version_id INT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by INT NOT NULL REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- 'active', 'archived', 'deprecated'

    -- Performance tracking
    total_executions BIGINT DEFAULT 0,
    avg_latency_ms DECIMAL(10, 2),
    avg_cost_usd DECIMAL(10, 6),
    avg_quality_score DECIMAL(3, 2),  -- 0.0-1.0

    CONSTRAINT fk_active_version FOREIGN KEY (active_version_id)
        REFERENCES prompt_versions(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX idx_prompt_templates_status ON prompt_templates(status);


-- ============================================================
-- PROMPT VERSIONS (Version Control)
-- ============================================================

CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,
    prompt_template_id INT NOT NULL REFERENCES prompt_templates(id) ON DELETE CASCADE,
    version_number INT NOT NULL,  -- Auto-incrementing per template

    -- Template content
    template TEXT NOT NULL,  -- Jinja2 template with variables
    variables JSONB NOT NULL,  -- Expected variables with types and defaults

    -- LLM parameters
    model_name VARCHAR(100),  -- 'gpt-4', 'claude-3-opus', etc.
    temperature DECIMAL(3, 2),
    max_tokens INT,
    top_p DECIMAL(3, 2),

    -- Change tracking
    change_description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by INT NOT NULL REFERENCES users(id),

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'draft',  -- 'draft', 'active', 'deprecated'

    -- Performance metrics (updated as version is used)
    execution_count BIGINT DEFAULT 0,
    avg_latency_ms DECIMAL(10, 2),
    avg_cost_usd DECIMAL(10, 6),
    avg_quality_score DECIMAL(3, 2),

    UNIQUE(prompt_template_id, version_number)
);

CREATE INDEX idx_prompt_versions_template ON prompt_versions(prompt_template_id);
CREATE INDEX idx_prompt_versions_status ON prompt_versions(status);


-- ============================================================
-- PROMPT EXECUTIONS (Audit and Performance Tracking)
-- ============================================================

CREATE TABLE prompt_executions (
    id BIGSERIAL PRIMARY KEY,
    prompt_version_id INT NOT NULL REFERENCES prompt_versions(id),

    -- Execution context
    executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    correlation_id VARCHAR(100),
    agent_id VARCHAR(255),

    -- Input/Output
    variables_used JSONB NOT NULL,  -- Actual variable values
    rendered_prompt TEXT,  -- Final rendered prompt
    llm_response TEXT,

    -- Metrics
    latency_ms INT,
    tokens_used INT,
    cost_usd DECIMAL(10, 6),

    -- Quality feedback
    quality_score DECIMAL(3, 2),  -- 0.0-1.0 (manual or automated)
    feedback TEXT,

    -- Error tracking
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT
);

CREATE INDEX idx_prompt_executions_version ON prompt_executions(prompt_version_id);
CREATE INDEX idx_prompt_executions_timestamp ON prompt_executions(executed_at);
CREATE INDEX idx_prompt_executions_correlation ON prompt_executions(correlation_id);


-- ============================================================
-- A/B TESTS
-- ============================================================

CREATE TABLE prompt_ab_tests (
    id SERIAL PRIMARY KEY,
    prompt_template_id INT NOT NULL REFERENCES prompt_templates(id),

    -- Test configuration
    version_a_id INT NOT NULL REFERENCES prompt_versions(id),
    version_b_id INT NOT NULL REFERENCES prompt_versions(id),
    traffic_split DECIMAL(3, 2) NOT NULL DEFAULT 0.5,  -- 0.5 = 50/50 split

    -- Test parameters
    sample_size INT NOT NULL,
    success_metric VARCHAR(100) NOT NULL,  -- 'quality_score', 'latency', 'cost'

    -- Test status
    status VARCHAR(50) NOT NULL DEFAULT 'running',  -- 'running', 'completed', 'stopped'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Results
    version_a_executions INT DEFAULT 0,
    version_a_avg_metric DECIMAL(10, 4),
    version_b_executions INT DEFAULT 0,
    version_b_avg_metric DECIMAL(10, 4),

    -- Winner
    winner_version_id INT REFERENCES prompt_versions(id),
    statistical_significance DECIMAL(5, 4),  -- p-value

    -- Metadata
    created_by INT NOT NULL REFERENCES users(id),
    notes TEXT
);

CREATE INDEX idx_ab_tests_template ON prompt_ab_tests(prompt_template_id);
CREATE INDEX idx_ab_tests_status ON prompt_ab_tests(status);
```

### 3.2 Prompt Service Implementation

```python
from jinja2 import Template, TemplateSyntaxError
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

@dataclass
class PromptTemplate:
    id: int
    name: str
    category: str
    active_version: Optional['PromptVersion']

@dataclass
class PromptVersion:
    id: int
    version_number: int
    template: str
    variables: Dict[str, Any]
    model_name: str
    temperature: float
    max_tokens: int


class PromptService:
    """Service for managing prompt templates and versions"""

    def __init__(self, db, cache):
        self.db = db
        self.cache = cache

    async def create_prompt(
        self,
        name: str,
        description: str,
        template: str,
        variables: Dict[str, Any],
        category: str,
        created_by: int,
        model_name: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> PromptTemplate:
        """Create new prompt template with initial version"""

        # Validate template syntax
        try:
            Template(template)
        except TemplateSyntaxError as e:
            raise ValueError(f"Invalid Jinja2 template: {e}")

        # Create prompt template
        async with self.db.transaction():
            # Insert template
            prompt_id = await self.db.fetchval(
                """
                INSERT INTO prompt_templates (name, description, category, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                name, description, category, created_by
            )

            # Create version 1
            version_id = await self.db.fetchval(
                """
                INSERT INTO prompt_versions (
                    prompt_template_id, version_number, template, variables,
                    model_name, temperature, max_tokens, created_by, status
                )
                VALUES ($1, 1, $2, $3, $4, $5, $6, $7, 'active')
                RETURNING id
                """,
                prompt_id, template, json.dumps(variables),
                model_name, temperature, max_tokens, created_by
            )

            # Set as active version
            await self.db.execute(
                """
                UPDATE prompt_templates
                SET active_version_id = $1
                WHERE id = $2
                """,
                version_id, prompt_id
            )

        # Invalidate cache
        await self.cache.delete(f"prompt:{name}")

        return await self.get_prompt(prompt_id)

    async def create_version(
        self,
        prompt_id: int,
        template: str,
        variables: Dict[str, Any],
        change_description: str,
        created_by: int,
        **llm_params
    ) -> PromptVersion:
        """Create new version of existing prompt"""

        # Validate template
        try:
            Template(template)
        except TemplateSyntaxError as e:
            raise ValueError(f"Invalid Jinja2 template: {e}")

        # Get next version number
        next_version = await self.db.fetchval(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM prompt_versions
            WHERE prompt_template_id = $1
            """,
            prompt_id
        )

        # Create new version
        version_id = await self.db.fetchval(
            """
            INSERT INTO prompt_versions (
                prompt_template_id, version_number, template, variables,
                change_description, created_by, status,
                model_name, temperature, max_tokens
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'draft', $7, $8, $9)
            RETURNING id
            """,
            prompt_id, next_version, template, json.dumps(variables),
            change_description, created_by,
            llm_params.get('model_name', 'gpt-4'),
            llm_params.get('temperature', 0.7),
            llm_params.get('max_tokens', 500)
        )

        return await self.get_version(prompt_id, next_version)

    async def activate_version(self, prompt_id: int, version_number: int):
        """Activate a specific version (make it the active version)"""

        version = await self.get_version(prompt_id, version_number)
        if not version:
            raise ValueError("Version not found")

        # Update active version
        await self.db.execute(
            """
            UPDATE prompt_templates
            SET active_version_id = $1, updated_at = NOW()
            WHERE id = $2
            """,
            version.id, prompt_id
        )

        # Update version status
        await self.db.execute(
            """
            UPDATE prompt_versions
            SET status = CASE
                WHEN id = $1 THEN 'active'
                ELSE 'deprecated'
            END
            WHERE prompt_template_id = $2 AND status = 'active'
            """,
            version.id, prompt_id
        )

        # Invalidate cache
        await self._invalidate_prompt_cache(prompt_id)

    async def render_template(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render Jinja2 template with variables"""

        try:
            jinja_template = Template(template)
            return jinja_template.render(**variables)
        except Exception as e:
            raise ValueError(f"Template rendering error: {e}")

    async def get_active_prompt(self, name: str) -> Optional[PromptTemplate]:
        """Get active version of prompt by name (cached)"""

        # Try cache first
        cache_key = f"prompt:{name}"
        cached = await self.cache.get(cache_key)
        if cached:
            return PromptTemplate(**json.loads(cached))

        # Fetch from database
        row = await self.db.fetchrow(
            """
            SELECT
                pt.id, pt.name, pt.category,
                pv.id as version_id, pv.version_number, pv.template,
                pv.variables, pv.model_name, pv.temperature, pv.max_tokens
            FROM prompt_templates pt
            JOIN prompt_versions pv ON pt.active_version_id = pv.id
            WHERE pt.name = $1 AND pt.status = 'active'
            """,
            name
        )

        if not row:
            return None

        prompt = PromptTemplate(
            id=row['id'],
            name=row['name'],
            category=row['category'],
            active_version=PromptVersion(
                id=row['version_id'],
                version_number=row['version_number'],
                template=row['template'],
                variables=row['variables'],
                model_name=row['model_name'],
                temperature=row['temperature'],
                max_tokens=row['max_tokens']
            )
        )

        # Cache for 5 minutes
        await self.cache.setex(
            cache_key,
            300,
            json.dumps(prompt.__dict__)
        )

        return prompt

    async def track_execution(
        self,
        version_id: int,
        variables_used: Dict[str, Any],
        rendered_prompt: str,
        llm_response: str,
        latency_ms: int,
        tokens_used: int,
        cost_usd: float,
        correlation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        quality_score: Optional[float] = None
    ):
        """Track prompt execution for analytics"""

        await self.db.execute(
            """
            INSERT INTO prompt_executions (
                prompt_version_id, correlation_id, agent_id,
                variables_used, rendered_prompt, llm_response,
                latency_ms, tokens_used, cost_usd, quality_score
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            version_id, correlation_id, agent_id,
            json.dumps(variables_used), rendered_prompt, llm_response,
            latency_ms, tokens_used, cost_usd, quality_score
        )

        # Update version metrics (async)
        await self._update_version_metrics(version_id)

    async def _update_version_metrics(self, version_id: int):
        """Update aggregated metrics for version"""

        await self.db.execute(
            """
            UPDATE prompt_versions
            SET
                execution_count = (
                    SELECT COUNT(*) FROM prompt_executions
                    WHERE prompt_version_id = $1 AND error_occurred = FALSE
                ),
                avg_latency_ms = (
                    SELECT AVG(latency_ms) FROM prompt_executions
                    WHERE prompt_version_id = $1 AND error_occurred = FALSE
                ),
                avg_cost_usd = (
                    SELECT AVG(cost_usd) FROM prompt_executions
                    WHERE prompt_version_id = $1 AND error_occurred = FALSE
                ),
                avg_quality_score = (
                    SELECT AVG(quality_score) FROM prompt_executions
                    WHERE prompt_version_id = $1
                      AND error_occurred = FALSE
                      AND quality_score IS NOT NULL
                )
            WHERE id = $1
            """,
            version_id
        )
```

### 3.3 Prompt Usage in Application

```python
class TrendSummarizer:
    """Example: Using managed prompts in application code"""

    def __init__(self, prompt_service: PromptService, llm_client):
        self.prompt_service = prompt_service
        self.llm_client = llm_client

    async def summarize_trend(
        self,
        trend_title: str,
        topics: List[str],
        max_words: int = 50
    ) -> str:
        """Summarize trend using managed prompt"""

        start_time = time.time()

        # Get active prompt template
        prompt = await self.prompt_service.get_active_prompt(
            name="trend_summarization"
        )

        if not prompt or not prompt.active_version:
            raise ValueError("Prompt 'trend_summarization' not found")

        # Prepare variables
        variables = {
            "trend_title": trend_title,
            "topics": "\n".join(f"- {topic}" for topic in topics),
            "max_words": max_words
        }

        # Render template
        rendered = await self.prompt_service.render_template(
            template=prompt.active_version.template,
            variables=variables
        )

        # Execute LLM call
        response = await self.llm_client.complete(
            prompt=rendered,
            model=prompt.active_version.model_name,
            temperature=prompt.active_version.temperature,
            max_tokens=prompt.active_version.max_tokens
        )

        # Track execution
        latency_ms = int((time.time() - start_time) * 1000)

        await self.prompt_service.track_execution(
            version_id=prompt.active_version.id,
            variables_used=variables,
            rendered_prompt=rendered,
            llm_response=response.text,
            latency_ms=latency_ms,
            tokens_used=response.usage.total_tokens,
            cost_usd=response.usage.total_tokens * 0.00002
        )

        return response.text
```

---

## 4. Configuration Management

### 4.1 Configuration Schema

```sql
-- ============================================================
-- CONFIGURATION DEFINITIONS
-- ============================================================

CREATE TABLE config_definitions (
    key VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL,
    value_type VARCHAR(50) NOT NULL,  -- 'string', 'int', 'float', 'bool', 'json'
    default_value TEXT,

    -- Validation
    validation_schema JSONB,  -- JSON schema for validation
    min_value DECIMAL(20, 6),  -- For numeric types
    max_value DECIMAL(20, 6),
    allowed_values TEXT[],  -- For enum types

    -- Categorization
    category VARCHAR(100) NOT NULL,  -- 'llm', 'trend_detection', 'agents', etc.
    subcategory VARCHAR(100),

    -- Change management
    requires_approval BOOLEAN DEFAULT FALSE,
    requires_restart BOOLEAN DEFAULT FALSE,  -- If change needs service restart

    -- Documentation
    documentation_url TEXT,
    example_value TEXT
);

INSERT INTO config_definitions (key, description, value_type, default_value, category, requires_approval) VALUES
('llm.default_model', 'Default LLM model for general tasks', 'string', 'gpt-4', 'llm', false),
('llm.default_temperature', 'Default temperature for LLM calls', 'float', '0.7', 'llm', false),
('llm.max_tokens_default', 'Default max tokens for LLM responses', 'int', '500', 'llm', false),
('llm.cost_per_1k_tokens', 'Cost per 1000 tokens (USD)', 'float', '0.03', 'llm', true),

('trend_detection.min_cluster_size', 'Minimum items to form a trend', 'int', '5', 'trend_detection', false),
('trend_detection.similarity_threshold', 'Similarity threshold for clustering (0-1)', 'float', '0.75', 'trend_detection', false),
('trend_detection.viral_threshold', 'Score threshold for VIRAL state', 'int', '1000', 'trend_detection', false),

('agents.default_daily_budget_usd', 'Default daily budget for new agents', 'float', '50.0', 'agents', true),
('agents.circuit_breaker_cooldown_seconds', 'Circuit breaker cooldown period', 'int', '600', 'agents', false);


-- ============================================================
-- CONFIGURATION VALUES (Current State)
-- ============================================================

CREATE TABLE config_values (
    key VARCHAR(255) PRIMARY KEY REFERENCES config_definitions(key),
    value TEXT NOT NULL,

    -- Change tracking
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_by INT REFERENCES users(id),

    -- Environment-specific overrides
    environment VARCHAR(50),  -- 'dev', 'staging', 'prod', NULL for all

    UNIQUE(key, environment)
);


-- ============================================================
-- CONFIGURATION HISTORY
-- ============================================================

CREATE TABLE config_history (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,

    -- Change metadata
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    changed_by INT NOT NULL REFERENCES users(id),
    change_reason TEXT,

    -- Rollback tracking
    rolled_back BOOLEAN DEFAULT FALSE,
    rolled_back_at TIMESTAMP WITH TIME ZONE,
    rolled_back_by INT REFERENCES users(id)
);

CREATE INDEX idx_config_history_key ON config_history(key);
CREATE INDEX idx_config_history_timestamp ON config_history(changed_at);
```

### 4.2 Configuration Service

```python
from typing import Any, Optional, Union
import json
from datetime import datetime


class ConfigService:
    """Hierarchical configuration service with hot-reload"""

    def __init__(self, db, cache, environment: str = 'prod'):
        self.db = db
        self.cache = cache
        self.environment = environment
        self._watchers = []  # Callbacks for config changes

    async def get_config(
        self,
        key: str,
        default: Optional[Any] = None
    ) -> Any:
        """Get configuration value (with caching)"""

        cache_key = f"config:{self.environment}:{key}"

        # Try cache
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return self._deserialize_value(cached)

        # Fetch from database (environment-specific, then fallback to global)
        row = await self.db.fetchrow(
            """
            SELECT cv.value, cd.value_type
            FROM config_values cv
            JOIN config_definitions cd ON cv.key = cd.key
            WHERE cv.key = $1
              AND (cv.environment = $2 OR cv.environment IS NULL)
            ORDER BY cv.environment DESC NULLS LAST
            LIMIT 1
            """,
            key, self.environment
        )

        if not row:
            # Use default from definition
            row = await self.db.fetchrow(
                """
                SELECT default_value as value, value_type
                FROM config_definitions
                WHERE key = $1
                """,
                key
            )

        if not row:
            return default

        # Deserialize based on type
        value = self._parse_value(row['value'], row['value_type'])

        # Cache for 5 minutes
        await self.cache.setex(cache_key, 300, row['value'])

        return value

    async def update_config(
        self,
        key: str,
        value: Any,
        updated_by: int,
        reason: Optional[str] = None,
        environment: Optional[str] = None
    ):
        """Update configuration value"""

        # Get definition
        definition = await self.db.fetchrow(
            "SELECT * FROM config_definitions WHERE key = $1",
            key
        )

        if not definition:
            raise ValueError(f"Unknown config key: {key}")

        # Validate value
        validation_error = self._validate_value(
            value,
            definition['value_type'],
            definition
        )
        if validation_error:
            raise ValueError(validation_error)

        # Serialize value
        serialized = self._serialize_value(value, definition['value_type'])

        # Get current value for history
        current_value = await self.get_config(key)

        # Update or insert
        await self.db.execute(
            """
            INSERT INTO config_values (key, value, updated_by, environment)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (key, environment) DO UPDATE
            SET value = $2, updated_at = NOW(), updated_by = $3
            """,
            key, serialized, updated_by, environment or self.environment
        )

        # Record history
        await self.db.execute(
            """
            INSERT INTO config_history (key, old_value, new_value, changed_by, change_reason)
            VALUES ($1, $2, $3, $4, $5)
            """,
            key, str(current_value), serialized, updated_by, reason
        )

        # Invalidate cache
        await self._invalidate_config_cache(key)

        # Notify watchers
        await self._notify_watchers(key, current_value, value)

    async def reload_config(self, key: str):
        """Hot-reload configuration (notify all services)"""

        # Invalidate cache
        await self._invalidate_config_cache(key)

        # Publish reload event
        await self.event_bus.publish(
            "config.reloaded",
            {
                "key": key,
                "environment": self.environment,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def rollback_config(
        self,
        history_id: int,
        rolled_back_by: int
    ):
        """Rollback configuration to previous value"""

        # Get history entry
        history = await self.db.fetchrow(
            "SELECT * FROM config_history WHERE id = $1",
            history_id
        )

        if not history or history['rolled_back']:
            raise ValueError("Invalid or already rolled back")

        # Restore old value
        await self.update_config(
            key=history['key'],
            value=history['old_value'],
            updated_by=rolled_back_by,
            reason=f"Rollback from history entry {history_id}"
        )

        # Mark as rolled back
        await self.db.execute(
            """
            UPDATE config_history
            SET rolled_back = TRUE, rolled_back_at = NOW(), rolled_back_by = $1
            WHERE id = $2
            """,
            rolled_back_by, history_id
        )

    def _validate_value(
        self,
        value: Any,
        value_type: str,
        definition: dict
    ) -> Optional[str]:
        """Validate configuration value"""

        # Type validation
        if value_type == 'int':
            try:
                int_value = int(value)
                if definition['min_value'] and int_value < definition['min_value']:
                    return f"Value below minimum: {definition['min_value']}"
                if definition['max_value'] and int_value > definition['max_value']:
                    return f"Value above maximum: {definition['max_value']}"
            except (ValueError, TypeError):
                return f"Invalid integer value: {value}"

        elif value_type == 'float':
            try:
                float_value = float(value)
                if definition['min_value'] and float_value < float(definition['min_value']):
                    return f"Value below minimum: {definition['min_value']}"
                if definition['max_value'] and float_value > float(definition['max_value']):
                    return f"Value above maximum: {definition['max_value']}"
            except (ValueError, TypeError):
                return f"Invalid float value: {value}"

        elif value_type == 'bool':
            if not isinstance(value, bool) and str(value).lower() not in ('true', 'false', '1', '0'):
                return f"Invalid boolean value: {value}"

        elif value_type == 'json':
            try:
                json.loads(value if isinstance(value, str) else json.dumps(value))
            except json.JSONDecodeError:
                return f"Invalid JSON value: {value}"

        # Enum validation
        if definition['allowed_values']:
            if str(value) not in definition['allowed_values']:
                return f"Value must be one of: {definition['allowed_values']}"

        return None

    def _parse_value(self, value: str, value_type: str) -> Any:
        """Parse string value to typed value"""

        if value_type == 'int':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type == 'bool':
            return value.lower() in ('true', '1', 'yes')
        elif value_type == 'json':
            return json.loads(value)
        else:
            return value

    def _serialize_value(self, value: Any, value_type: str) -> str:
        """Serialize value to string for storage"""

        if value_type == 'json':
            return json.dumps(value)
        else:
            return str(value)

    async def _invalidate_config_cache(self, key: str):
        """Invalidate cache for all environments"""

        for env in ['dev', 'staging', 'prod']:
            await self.cache.delete(f"config:{env}:{key}")

    async def _notify_watchers(self, key: str, old_value: Any, new_value: Any):
        """Notify registered watchers of config change"""

        for watcher in self._watchers:
            try:
                await watcher(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Config watcher error: {e}")

    def watch_config(self, callback):
        """Register callback for config changes"""
        self._watchers.append(callback)
```

### 4.3 Hot-Reload Example

```python
class TrendDetectionService:
    """Example: Service that responds to config changes"""

    def __init__(self, config_service: ConfigService):
        self.config = config_service

        # Initial load
        self.min_cluster_size = None
        self.similarity_threshold = None

        # Watch for config changes
        self.config.watch_config(self._on_config_change)

        # Load initial values
        asyncio.create_task(self._load_config())

    async def _load_config(self):
        """Load configuration values"""

        self.min_cluster_size = await self.config.get_config(
            'trend_detection.min_cluster_size',
            default=5
        )
        self.similarity_threshold = await self.config.get_config(
            'trend_detection.similarity_threshold',
            default=0.75
        )

        logger.info(
            f"Config loaded: min_cluster_size={self.min_cluster_size}, "
            f"similarity_threshold={self.similarity_threshold}"
        )

    async def _on_config_change(self, key: str, old_value: Any, new_value: Any):
        """Handle configuration changes"""

        if key == 'trend_detection.min_cluster_size':
            logger.info(f"Updating min_cluster_size: {old_value} -> {new_value}")
            self.min_cluster_size = new_value

        elif key == 'trend_detection.similarity_threshold':
            logger.info(f"Updating similarity_threshold: {old_value} -> {new_value}")
            self.similarity_threshold = new_value
```

---

## 5. Agent Control Plane Administration

### 5.1 Agent Management UI Screens

**Agent Dashboard:**

```
┌────────────────────────────────────────────────────────────────┐
│ Agent Control Plane Dashboard                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Active Agents: 15        Suspended: 2        Total Tasks: 1.2k│
│  Budget Usage: $245 / $500 daily                                │
│  Circuit Breakers Tripped: 3                                    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Agent List                                                │  │
│  ├────────────┬─────────┬─────────┬──────────┬─────────────┤  │
│  │ Agent ID   │ Status  │ Tasks   │ Budget   │ Trust Level │  │
│  ├────────────┼─────────┼─────────┼──────────┼─────────────┤  │
│  │ research_1 │ Active  │ 45      │ $12/$50  │ STANDARD    │  │
│  │ analyst_2  │ Active  │ 23      │ $8/$50   │ ELEVATED    │  │
│  │ worker_3   │ Warning │ 12      │ $48/$50  │ BASIC       │  │
│  │ research_4 │ Tripped │ 0       │ $0/$50   │ STANDARD    │  │
│  └────────────┴─────────┴─────────┴──────────┴─────────────┘  │
│                                                                 │
│  [View All Agents]  [Add Agent]  [Bulk Actions ▼]             │
└────────────────────────────────────────────────────────────────┘
```

**Agent Detail View:**

```
┌────────────────────────────────────────────────────────────────┐
│ Agent: research_assistant_v2                      [Edit] [⚙]   │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐  ┌────────────────────────────────┐  │
│  │ Budget Configuration│  │ Performance Metrics             │  │
│  ├─────────────────────┤  ├────────────────────────────────┤  │
│  │ Daily: $12 / $50    │  │ Success Rate: 98.5%             │  │
│  │ Monthly: $245/$1000 │  │ Avg Latency: 2.3s               │  │
│  │ Tokens: 120k/1M     │  │ Total Tasks: 1,234              │  │
│  │ Concurrent: 2/5     │  │ Failed Tasks: 18                │  │
│  │                     │  │                                  │  │
│  │ [Increase Budget]   │  │ [View Details]                  │  │
│  └─────────────────────┘  └────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Recent Tasks                                              │  │
│  ├──────────┬─────────────┬─────────┬──────────────────────┤  │
│  │ Task ID  │ Type        │ Status  │ Duration             │  │
│  ├──────────┼─────────────┼─────────┼──────────────────────┤  │
│  │ T-1234   │ Collection  │ ✓       │ 2.1s                 │  │
│  │ T-1235   │ Analysis    │ ✓       │ 3.4s                 │  │
│  │ T-1236   │ Summary     │ Running │ 1.2s                 │  │
│  └──────────┴─────────────┴─────────┴──────────────────────┘  │
│                                                                 │
│  Trust Level: ⭐⭐⭐ STANDARD   [Change Trust Level]             │
│  Circuit Breaker: OK           [Manual Trip]                   │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 Circuit Breaker Management

```python
@router.get("/admin/circuit-breakers")
async def list_circuit_breakers(
    status: Optional[str] = None,  # 'tripped', 'ok'
    admin_user = Depends(require_admin)
):
    """List all circuit breakers"""

    query = """
    SELECT
        correlation_id,
        tripped_at,
        reset_at,
        reason,
        (SELECT COUNT(*) FROM lineage_graph WHERE correlation_id = cb.correlation_id) as graph_size
    FROM circuit_breakers cb
    WHERE ($1 IS NULL OR status = $1)
    ORDER BY tripped_at DESC
    LIMIT 100
    """

    breakers = await db.fetch(query, status)

    return {
        "circuit_breakers": [
            {
                "correlation_id": b['correlation_id'],
                "tripped_at": b['tripped_at'],
                "reset_at": b['reset_at'],
                "reason": b['reason'],
                "graph_size": b['graph_size'],
                "is_tripped": b['reset_at'] is None or b['reset_at'] > datetime.utcnow()
            }
            for b in breakers
        ]
    }


@router.get("/admin/circuit-breakers/{correlation_id}/graph")
async def get_causality_graph(
    correlation_id: str,
    admin_user = Depends(require_admin)
):
    """Get causality graph for visualization"""

    # Build lineage graph
    graph = await lineage_tracker.build_lineage_graph(correlation_id)

    # Detect cycles
    cycles = list(nx.simple_cycles(graph))

    # Convert to visualization format
    nodes = []
    edges = []

    for node in graph.nodes:
        nodes.append({
            "id": node,
            "label": node,
            "type": node.split('_')[0]  # agent, task, trend, event
        })

    for source, target, data in graph.edges(data=True):
        edges.append({
            "source": source,
            "target": target,
            "action": data.get('action_type'),
            "timestamp": data.get('timestamp').isoformat() if data.get('timestamp') else None
        })

    return {
        "correlation_id": correlation_id,
        "graph": {
            "nodes": nodes,
            "edges": edges
        },
        "cycles": cycles,
        "has_loop": len(cycles) > 0
    }
```

---

## 6. Data Management Interface

### 6.1 Trend Curation Tools

```python
@router.post("/admin/trends/merge")
async def merge_trends(
    request: MergeTrendsRequest,
    admin_user = Depends(require_permission("data.merge-trends"))
):
    """
    Merge multiple trends into one

    Merge strategies:
    - PRIMARY: Use primary trend's title/summary, merge topics
    - NEWEST: Use newest trend's title/summary
    - HIGHEST_SCORE: Use highest scoring trend
    - CUSTOM: Admin provides new title/summary
    """

    if len(request.trend_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 trends")

    # Validate all trends exist
    trends = await db.fetch(
        "SELECT * FROM trends WHERE id = ANY($1)",
        request.trend_ids
    )

    if len(trends) != len(request.trend_ids):
        raise HTTPException(status_code=404, detail="Some trends not found")

    # Determine primary trend based on strategy
    if request.strategy == "PRIMARY":
        primary = next(t for t in trends if t['id'] == request.primary_trend_id)
    elif request.strategy == "NEWEST":
        primary = max(trends, key=lambda t: t['created_at'])
    elif request.strategy == "HIGHEST_SCORE":
        primary = max(trends, key=lambda t: t['score'])
    elif request.strategy == "CUSTOM":
        primary = None  # Will use custom values

    # Merge topics from all trends
    all_topic_ids = []
    for trend in trends:
        topic_ids = await db.fetchval(
            "SELECT array_agg(topic_id) FROM trend_topics WHERE trend_id = $1",
            trend['id']
        )
        if topic_ids:
            all_topic_ids.extend(topic_ids)

    # Deduplicate topics
    unique_topic_ids = list(set(all_topic_ids))

    # Create merged trend
    async with db.transaction():
        # Insert merged trend
        merged_id = await db.fetchval(
            """
            INSERT INTO trends (
                title, summary, category, language, state, score,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING id
            """,
            request.custom_title or primary['title'],
            request.custom_summary or primary['summary'],
            primary['category'],
            primary['language'],
            max(t['state'] for t in trends),  # Highest state
            sum(t['score'] for t in trends)  # Sum scores
        )

        # Link all topics to merged trend
        for topic_id in unique_topic_ids:
            await db.execute(
                """
                INSERT INTO trend_topics (trend_id, topic_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                merged_id, topic_id
            )

        # Archive original trends
        await db.execute(
            """
            UPDATE trends
            SET state = 'ARCHIVED', merged_into = $1, updated_at = NOW()
            WHERE id = ANY($2)
            """,
            merged_id, request.trend_ids
        )

        # Log merge operation
        await db.execute(
            """
            INSERT INTO admin_operations (
                operation_type, operator_id, details
            )
            VALUES ('merge_trends', $1, $2)
            """,
            admin_user.id,
            json.dumps({
                "merged_trend_id": merged_id,
                "source_trend_ids": request.trend_ids,
                "strategy": request.strategy
            })
        )

    # Return merged trend
    merged_trend = await db.fetchrow(
        "SELECT * FROM trends WHERE id = $1",
        merged_id
    )

    return {"merged_trend": dict(merged_trend)}


@router.post("/admin/trends/bulk-delete")
async def bulk_delete_trends(
    request: BulkDeleteRequest,
    admin_user = Depends(require_permission("data.delete-trends"))
):
    """Bulk delete trends (with safety checks)"""

    # Validate not deleting too many at once
    if len(request.trend_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete more than 100 trends at once"
        )

    # Soft delete (mark as deleted, keep data)
    deleted_count = await db.fetchval(
        """
        UPDATE trends
        SET state = 'DELETED', deleted_at = NOW(), deleted_by = $1
        WHERE id = ANY($2)
        RETURNING COUNT(*)
        """,
        admin_user.id, request.trend_ids
    )

    # Log operation
    await audit_log.log_change(
        user_id=admin_user.id,
        action="trends.bulk_deleted",
        resource_type="trend",
        resource_id=None,
        changes={
            "count": deleted_count,
            "trend_ids": request.trend_ids
        }
    )

    return {"deleted_count": deleted_count}
```

### 6.2 Source Management

```python
@router.post("/admin/sources")
async def add_data_source(
    request: AddSourceRequest,
    admin_user = Depends(require_permission("sources.create"))
):
    """Add new data source"""

    # Validate source type
    if request.source_type not in ['twitter', 'reddit', 'rss', 'api']:
        raise HTTPException(status_code=400, detail="Invalid source type")

    # Validate configuration
    validation = await source_validator.validate_config(
        source_type=request.source_type,
        config=request.config
    )

    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source config: {validation.error}"
        )

    # Create source
    source_id = await db.fetchval(
        """
        INSERT INTO data_sources (
            name, source_type, config, category, language,
            collection_interval, is_active, created_by
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        request.name,
        request.source_type,
        json.dumps(request.config),
        request.category,
        request.language,
        request.collection_interval,
        request.is_active,
        admin_user.id
    )

    # Test connection if requested
    if request.test_connection:
        test_result = await source_tester.test_source(source_id)
        if not test_result.success:
            # Rollback and return error
            await db.execute("DELETE FROM data_sources WHERE id = $1", source_id)
            raise HTTPException(
                status_code=400,
                detail=f"Source connection test failed: {test_result.error}"
            )

    return {"source_id": source_id, "status": "created"}
```

---

## 7. User & Access Control

### 7.1 RBAC Schema

```sql
-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    -- Profile
    full_name VARCHAR(255),
    avatar_url TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,  -- Super admin bypass
    email_verified BOOLEAN DEFAULT FALSE,

    -- MFA
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;


-- ============================================================
-- ROLES
-- ============================================================

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,

    -- System roles cannot be deleted
    is_system BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed system roles
INSERT INTO roles (name, description, is_system) VALUES
('admin', 'Full system access', true),
('operator', 'Operational tasks (config, agents, data)', true),
('analyst', 'Read-only access to all data', true),
('developer', 'API access and prompt management', true);


-- ============================================================
-- PERMISSIONS
-- ============================================================

CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,  -- 'prompts.create', 'config.update'
    description TEXT,
    resource_type VARCHAR(100),  -- 'prompt', 'config', 'agent'
    action VARCHAR(100)  -- 'create', 'read', 'update', 'delete'
);

-- Seed permissions
INSERT INTO permissions (name, description, resource_type, action) VALUES
-- Prompts
('prompts.read', 'View prompts', 'prompt', 'read'),
('prompts.create', 'Create prompts', 'prompt', 'create'),
('prompts.update', 'Update prompts', 'prompt', 'update'),
('prompts.delete', 'Delete prompts', 'prompt', 'delete'),
('prompts.ab-test', 'Run A/B tests', 'prompt', 'test'),

-- Configuration
('config.read', 'View configuration', 'config', 'read'),
('config.update', 'Update configuration', 'config', 'update'),
('config.reload', 'Hot-reload configuration', 'config', 'reload'),

-- Agents
('agents.read', 'View agents', 'agent', 'read'),
('agents.update-budget', 'Update agent budgets', 'agent', 'update'),
('agents.circuit-breaker', 'Manage circuit breakers', 'agent', 'manage'),

-- Data
('data.read', 'View trends and data', 'trend', 'read'),
('data.merge-trends', 'Merge trends', 'trend', 'merge'),
('data.delete-trends', 'Delete trends', 'trend', 'delete'),

-- Sources
('sources.create', 'Add data sources', 'source', 'create'),
('sources.update', 'Update data sources', 'source', 'update'),
('sources.delete', 'Remove data sources', 'source', 'delete');


-- ============================================================
-- ROLE PERMISSIONS (Many-to-Many)
-- ============================================================

CREATE TABLE role_permissions (
    role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,

    PRIMARY KEY (role_id, permission_id)
);

-- Assign permissions to roles
-- Admin: all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'admin';

-- Operator: most permissions except delete
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'operator'
  AND p.name NOT LIKE '%.delete';


-- ============================================================
-- USER ROLES (Many-to-Many)
-- ============================================================

CREATE TABLE user_roles (
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,

    granted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    granted_by INT REFERENCES users(id),

    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);


-- ============================================================
-- API KEYS
-- ============================================================

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Key
    key_hash VARCHAR(255) NOT NULL UNIQUE,  -- Hash of actual key
    key_prefix VARCHAR(20) NOT NULL,  -- First few chars for identification
    name VARCHAR(255),

    -- Permissions (scoped API key)
    scopes TEXT[],  -- ['read:trends', 'write:tasks']

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Usage tracking
    last_used_at TIMESTAMP WITH TIME ZONE,
    total_requests BIGINT DEFAULT 0,

    -- Lifecycle
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoked_by INT REFERENCES users(id)
);

CREATE INDEX idx_api_keys_user ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = TRUE;
```

### 7.2 Permission Check System

```python
from functools import wraps
from typing import List, Optional

class PermissionChecker:
    """Check user permissions"""

    def __init__(self, db, cache):
        self.db = db
        self.cache = cache

    async def has_permission(
        self,
        user_id: int,
        permission: str
    ) -> bool:
        """Check if user has specific permission"""

        # Check cache
        cache_key = f"user_permissions:{user_id}"
        cached_perms = await self.cache.get(cache_key)

        if cached_perms:
            return permission in json.loads(cached_perms)

        # Query database
        permissions = await self.db.fetchval(
            """
            SELECT array_agg(DISTINCT p.name)
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = $1 AND u.is_active = TRUE
            """,
            user_id
        )

        if not permissions:
            permissions = []

        # Cache for 5 minutes
        await self.cache.setex(
            cache_key,
            300,
            json.dumps(permissions)
        )

        return permission in permissions

    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for user"""

        permissions = await self.db.fetch(
            """
            SELECT DISTINCT p.name, p.description, p.resource_type, p.action
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE u.id = $1 AND u.is_active = TRUE
            ORDER BY p.resource_type, p.action
            """,
            user_id
        )

        return [dict(p) for p in permissions]

    async def invalidate_user_cache(self, user_id: int):
        """Invalidate permission cache when roles change"""

        await self.cache.delete(f"user_permissions:{user_id}")


# Decorator for FastAPI endpoints
def require_permission(permission: str):
    """Decorator to require specific permission"""

    async def _check(
        current_user: User = Depends(get_current_user),
        permission_checker: PermissionChecker = Depends(get_permission_checker)
    ):
        # Super admin bypass
        if current_user.is_admin:
            return current_user

        # Check permission
        has_perm = await permission_checker.has_permission(
            current_user.id,
            permission
        )

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )

        return current_user

    return _check
```

---

## 8. Admin UI Architecture

### 8.1 Technology Stack

**Frontend:**
- **React 18+** with TypeScript
- **React Admin** framework for admin interfaces
- **TanStack Query** for data fetching
- **Tailwind CSS** for styling
- **Recharts** for visualization

**Component Structure:**

```
src/admin/
├── components/
│   ├── PromptEditor/
│   │   ├── PromptList.tsx
│   │   ├── PromptForm.tsx
│   │   ├── VersionHistory.tsx
│   │   ├── ABTestManager.tsx
│   │   └── TemplatePreview.tsx
│   ├── ConfigManager/
│   │   ├── ConfigTree.tsx
│   │   ├── ConfigEditor.tsx
│   │   ├── ConfigHistory.tsx
│   │   └── HotReloadStatus.tsx
│   ├── AgentDashboard/
│   │   ├── AgentList.tsx
│   │   ├── AgentDetail.tsx
│   │   ├── BudgetEditor.tsx
│   │   ├── CircuitBreakerManager.tsx
│   │   └── CausalityGraphViewer.tsx
│   ├── DataCurator/
│   │   ├── TrendList.tsx
│   │   ├── TrendMerger.tsx
│   │   ├── BulkActions.tsx
│   │   └── SourceManager.tsx
│   └── UserManager/
│       ├── UserList.tsx
│       ├── RoleEditor.tsx
│       ├── PermissionMatrix.tsx
│       └── APIKeyManager.tsx
├── pages/
│   ├── Dashboard.tsx
│   ├── Prompts.tsx
│   ├── Configuration.tsx
│   ├── Agents.tsx
│   ├── Data.tsx
│   └── Users.tsx
└── services/
    ├── adminApi.ts
    ├── authService.ts
    └── websocket.ts
```

### 8.2 Key UI Components

**Prompt Editor Example:**

```typescript
// components/PromptEditor/PromptForm.tsx

import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '../../services/adminApi';
import { MonacoEditor } from '@monaco-editor/react';

interface PromptFormProps {
  promptId?: number;
  onSuccess?: () => void;
}

export const PromptForm: React.FC<PromptFormProps> = ({ promptId, onSuccess }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('');
  const [category, setCategory] = useState('summarization');

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data) => adminApi.prompts.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['prompts']);
      onSuccess?.();
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    createMutation.mutate({
      name,
      description,
      template,
      category,
      variables: extractVariables(template)
    });
  };

  const extractVariables = (template: string): Record<string, any> => {
    // Extract {{ variable_name }} from Jinja2 template
    const regex = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g;
    const matches = [...template.matchAll(regex)];
    const variables: Record<string, any> = {};

    matches.forEach(match => {
      const varName = match[1];
      variables[varName] = {
        type: 'string',
        required: true,
        description: `Variable ${varName}`
      };
    });

    return variables;
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Prompt Name
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          placeholder="trend_summarization"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          rows={3}
          placeholder="Summarize trends for display..."
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Category
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          <option value="summarization">Summarization</option>
          <option value="classification">Classification</option>
          <option value="analysis">Analysis</option>
          <option value="extraction">Extraction</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Template (Jinja2)
        </label>
        <MonacoEditor
          height="300px"
          language="jinja"
          value={template}
          onChange={(value) => setTemplate(value || '')}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            wordWrap: 'on'
          }}
        />
        <p className="mt-2 text-sm text-gray-500">
          Use {'{{ variable_name }}'} for variables
        </p>
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={() => window.history.back()}
          className="px-4 py-2 border border-gray-300 rounded-md"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {createMutation.isPending ? 'Creating...' : 'Create Prompt'}
        </button>
      </div>
    </form>
  );
};
```

**Causality Graph Viewer:**

```typescript
// components/AgentDashboard/CausalityGraphViewer.tsx

import React, { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Network } from 'vis-network/standalone';
import { adminApi } from '../../services/adminApi';

interface CausalityGraphViewerProps {
  correlationId: string;
}

export const CausalityGraphViewer: React.FC<CausalityGraphViewerProps> = ({ correlationId }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['causality-graph', correlationId],
    queryFn: () => adminApi.circuitBreakers.getGraph(correlationId)
  });

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    // Prepare nodes
    const nodes = graphData.graph.nodes.map(node => ({
      id: node.id,
      label: node.id,
      color: getNodeColor(node.type),
      shape: getNodeShape(node.type)
    }));

    // Prepare edges
    const edges = graphData.graph.edges.map((edge, index) => ({
      id: index,
      from: edge.source,
      to: edge.target,
      label: edge.action,
      arrows: 'to'
    }));

    // Highlight cycles
    if (graphData.cycles && graphData.cycles.length > 0) {
      const cycleNodes = new Set(graphData.cycles[0]);
      nodes.forEach(node => {
        if (cycleNodes.has(node.id)) {
          node.color = '#ff4444';  // Red for loop
          node.borderWidth = 3;
        }
      });
    }

    // Create network
    networkRef.current = new Network(
      containerRef.current,
      { nodes, edges },
      {
        layout: {
          hierarchical: {
            direction: 'UD',
            sortMethod: 'directed'
          }
        },
        physics: {
          enabled: false
        },
        edges: {
          smooth: {
            type: 'cubicBezier'
          }
        }
      }
    );

    return () => {
      networkRef.current?.destroy();
    };
  }, [graphData]);

  const getNodeColor = (type: string): string => {
    switch (type) {
      case 'agent': return '#4CAF50';
      case 'task': return '#2196F3';
      case 'trend': return '#FF9800';
      case 'event': return '#9C27B0';
      default: return '#757575';
    }
  };

  const getNodeShape = (type: string): string => {
    switch (type) {
      case 'agent': return 'box';
      case 'task': return 'ellipse';
      case 'trend': return 'diamond';
      case 'event': return 'dot';
      default: return 'ellipse';
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-96">Loading graph...</div>;
  }

  return (
    <div className="space-y-4">
      {graphData?.has_loop && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <h3 className="text-red-800 font-semibold">⚠️ Feedback Loop Detected</h3>
          <p className="text-red-700 text-sm mt-1">
            Cycle: {graphData.cycles[0].join(' → ')}
          </p>
        </div>
      )}

      <div ref={containerRef} className="border border-gray-300 rounded-md h-96" />

      <div className="flex space-x-4 text-sm">
        <div className="flex items-center">
          <div className="w-4 h-4 bg-green-500 rounded mr-2" />
          <span>Agent</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-blue-500 rounded mr-2" />
          <span>Task</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-orange-500 rounded mr-2" />
          <span>Trend</span>
        </div>
        <div className="flex items-center">
          <div className="w-4 h-4 bg-purple-500 rounded mr-2" />
          <span>Event</span>
        </div>
      </div>
    </div>
  );
};
```

---

## 9. Security & Audit

### 9.1 Audit Logging

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,

    -- Who
    user_id INT REFERENCES users(id),
    user_email VARCHAR(255),
    ip_address INET,
    user_agent TEXT,

    -- What
    action VARCHAR(255) NOT NULL,  -- 'prompt.created', 'config.updated'
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),

    -- Changes
    old_values JSONB,
    new_values JSONB,

    -- When
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Context
    correlation_id VARCHAR(100),
    session_id VARCHAR(100),

    -- Risk assessment
    risk_level VARCHAR(50),  -- 'low', 'medium', 'high', 'critical'

    -- Additional context
    metadata JSONB
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
```

```python
class AuditLogger:
    """Comprehensive audit logging"""

    async def log_change(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: str,
        changes: dict,
        request: Request = None,
        risk_level: str = 'low'
    ):
        """Log administrative action"""

        # Get user info
        user = await self.db.fetchrow(
            "SELECT email FROM users WHERE id = $1",
            user_id
        )

        # Extract request metadata
        ip_address = None
        user_agent = None
        session_id = None

        if request:
            ip_address = request.client.host
            user_agent = request.headers.get('user-agent')
            session_id = request.cookies.get('session_id')

        # Determine old values based on resource
        old_values = await self._get_current_values(resource_type, resource_id)

        # Log to database
        await self.db.execute(
            """
            INSERT INTO audit_log (
                user_id, user_email, ip_address, user_agent,
                action, resource_type, resource_id,
                old_values, new_values,
                session_id, risk_level
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            user_id, user['email'], ip_address, user_agent,
            action, resource_type, resource_id,
            json.dumps(old_values) if old_values else None,
            json.dumps(changes),
            session_id, risk_level
        )

        # If high risk, send alert
        if risk_level in ['high', 'critical']:
            await self.alert_service.send_alert(
                severity='warning',
                title=f'High-risk admin action: {action}',
                message=f"User {user['email']} performed {action} on {resource_type}:{resource_id}",
                metadata=changes
            )
```

### 9.2 Change Approval Workflow

```python
@router.post("/admin/changes/{change_id}/approve")
async def approve_change(
    change_id: int,
    admin_user = Depends(require_permission("changes.approve"))
):
    """Approve pending change request"""

    # Get change request
    change = await db.fetchrow(
        "SELECT * FROM change_requests WHERE id = $1",
        change_id
    )

    if not change or change['status'] != 'pending':
        raise HTTPException(status_code=404, detail="Change not found or not pending")

    # Validate approver is not requester
    if change['requested_by'] == admin_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve your own change request"
        )

    # Apply change based on type
    if change['change_type'] == 'config.update':
        await config_service.update_config(
            key=change['resource_key'],
            value=change['new_value'],
            updated_by=admin_user.id,
            reason=f"Approved change request #{change_id}"
        )

    elif change['change_type'] == 'agent.budget_update':
        await agent_control_plane.budget_engine.update_budget(
            agent_id=change['resource_id'],
            **json.loads(change['new_value'])
        )

    # Update change request
    await db.execute(
        """
        UPDATE change_requests
        SET status = 'approved', approved_at = NOW(), approved_by = $1
        WHERE id = $2
        """,
        admin_user.id, change_id
    )

    # Log approval
    await audit_log.log_change(
        user_id=admin_user.id,
        action="change_request.approved",
        resource_type="change_request",
        resource_id=str(change_id),
        changes={"change_type": change['change_type']},
        risk_level="high"
    )

    return {"status": "approved", "applied": True}
```

---

## 10. Operations & Deployment

### 10.1 Deployment Architecture

```yaml
# docker-compose.admin.yml

version: '3.8'

services:
  admin-api:
    build:
      context: .
      dockerfile: Dockerfile.admin
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET=${JWT_SECRET}
      - ADMIN_CORS_ORIGINS=https://admin.example.com
    ports:
      - "8001:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - admin-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  admin-ui:
    build:
      context: ./admin-ui
      dockerfile: Dockerfile
    environment:
      - REACT_APP_API_URL=https://admin-api.example.com
    ports:
      - "3001:80"
    networks:
      - admin-network

  # Separate network for admin services
  networks:
    admin-network:
      driver: bridge
      internal: false  # Allow external access
```

### 10.2 Security Hardening

```python
# admin/security.py

from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
import jwt

security = HTTPBearer()

class AdminSecurity:
    """Admin-specific security measures"""

    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET')
        self.failed_logins = {}  # Track failed login attempts

    async def verify_admin_token(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> User:
        """Verify JWT token for admin access"""

        try:
            payload = jwt.decode(
                credentials.credentials,
                self.jwt_secret,
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Verify user has admin access
        user_id = payload.get('user_id')
        user = await self.get_user(user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive"
            )

        # Check if admin or has admin role
        if not user.is_admin:
            has_admin_role = await self.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM user_roles ur
                    JOIN roles r ON ur.role_id = r.id
                    WHERE ur.user_id = $1 AND r.name = 'admin'
                )
                """,
                user_id
            )

            if not has_admin_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )

        # Update last login
        await self.db.execute(
            "UPDATE users SET last_login_at = NOW() WHERE id = $1",
            user_id
        )

        return user

    async def rate_limit_check(self, ip_address: str, action: str):
        """Rate limiting for admin actions"""

        key = f"rate_limit:{ip_address}:{action}"

        # Check current count
        count = await self.redis.incr(key)

        if count == 1:
            # Set expiry on first request
            await self.redis.expire(key, 60)  # 1 minute window

        # Limit: 10 requests per minute
        if count > 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )

    async def track_failed_login(self, email: str, ip_address: str):
        """Track failed login attempts"""

        key = f"failed_login:{email}"

        # Increment failure count
        failures = await self.redis.incr(key)

        if failures == 1:
            await self.redis.expire(key, 900)  # 15 minutes

        # Lock account after 5 failed attempts
        if failures >= 5:
            await self.lock_account(email)

            # Alert security team
            await self.alert_service.send_alert(
                severity='critical',
                title=f'Account locked: {email}',
                message=f"5 failed login attempts from {ip_address}"
            )

        return failures
```

### 10.3 Monitoring & Alerts

```python
# Admin-specific metrics

admin_requests_total = Counter(
    'admin_requests_total',
    'Admin API requests',
    ['endpoint', 'method', 'status']
)

admin_changes_total = Counter(
    'admin_changes_total',
    'Admin changes made',
    ['change_type', 'user_id']
)

admin_change_approvals_pending = Gauge(
    'admin_change_approvals_pending',
    'Pending change approvals'
)

admin_failed_logins = Counter(
    'admin_failed_logins',
    'Failed admin login attempts',
    ['email']
)
```

---

## Appendices

### A. Configuration Reference

**Complete Config Categories:**

```yaml
# LLM Configuration
llm.default_model: "gpt-4"
llm.default_temperature: 0.7
llm.max_tokens_default: 500
llm.cost_per_1k_tokens: 0.03
llm.timeout_seconds: 30

# Trend Detection
trend_detection.min_cluster_size: 5
trend_detection.similarity_threshold: 0.75
trend_detection.viral_threshold: 1000
trend_detection.emerging_threshold: 100
trend_detection.declining_window_hours: 24

# Agent Control Plane
agents.default_daily_budget_usd: 50.0
agents.default_monthly_budget_usd: 1000.0
agents.circuit_breaker_cooldown_seconds: 600
agents.max_task_duration_seconds: 300
agents.loop_detection_max_depth: 20

# Memory System
memory.max_generation_depth: 5
memory.drift_threshold: 0.7
memory.ephemeral_ttl_seconds: 3600

# Event System
events.deduplication_window_seconds: 30
events.cascade_threshold: 2.0
events.max_fan_out: 5.0
```

### B. API Examples

**Complete Admin API Usage:**

```bash
# Login and get token
curl -X POST https://admin-api.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "secure_password"
  }'

# Response: { "access_token": "eyJ..." }

# Create prompt
curl -X POST https://admin-api.example.com/admin/prompts \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "trend_summarization",
    "description": "Summarize trends",
    "category": "summarization",
    "template": "Summarize this trend:\n\nTitle: {{ title }}\n\nTopics:\n{{ topics }}\n\nProvide a {{ max_words }}-word summary.",
    "variables": {
      "title": {"type": "string", "required": true},
      "topics": {"type": "string", "required": true},
      "max_words": {"type": "int", "default": 50}
    }
  }'

# Update configuration
curl -X PUT https://admin-api.example.com/admin/config/llm.default_temperature \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "value": "0.8",
    "justification": "Increase creativity for summaries"
  }'

# Merge trends
curl -X POST https://admin-api.example.com/admin/trends/merge \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "trend_ids": [123, 456, 789],
    "primary_trend_id": 123,
    "merge_strategy": "PRIMARY"
  }'
```

---

**Document Owner:** Platform Architecture Team
**Review Cycle:** Quarterly
**Next Review:** 2026-05-10
