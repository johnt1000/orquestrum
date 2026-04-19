# ARCHITECTURE - Login system (v1)

## Overview

Arquitetura simples para sistema de autenticação por e-mail/senha. Projeto pensado para ser light-weight e facilmente integrável com um frontend SPA.

## Components

- API Server (Node.js + Express)
- Database (Postgres)
- Session layer (server-side session store em Redis) ou JWT (opcional)
- Tests (Jest / Supertest)

## Data Flow

1. Cliente envia POST /register com email+senha
2. API valida entrada, cria user com password_hash e responde 201
3. Cliente envia POST /login com email+senha
4. API verifica hash, cria sessão (cookie HttpOnly) e responde 200
5. Cliente chama endpoints autenticados com cookie de sessão

## Technologies (v1 recommendation)

- Runtime: Node.js (>=18)
- Framework: Express
- DB: Postgres (UUIDs)
- Password hashing: bcrypt
- Session store: Redis (opcional) or JWT short-lived
- Testing: Jest + Supertest

## Decisions

- Usar bcrypt para hashing de senhas — justificativa: amplamente suportado e seguro para v1
- Usar sessions com cookie HttpOnly por simplicidade e menor superfície de ataque comparado a JWT armazenado em localStorage

## Risks

- Se usar JWT mal configurado, risco de permissão prolongada. Documentar TTLs.
- Implementação de lockout deve evitar DoS (não bloquear toda infra com muitos requests)

(architecture-v1)
