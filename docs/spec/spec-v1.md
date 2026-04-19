# SPEC - Login system (spec-v1)

## Objective

Construir um sistema simples de login que permita a usuários se registrar, autenticar e encerrar sessão de forma segura e auditável. A primeira versão (v1) foca na autenticação por e-mail/senha com armazenamento seguro das credenciais.

## Requirements

- Registro de usuário com e-mail e senha
- Login (autenticação) usando e-mail e senha
- Logout (encerrar sessão)
- Armazenamento seguro de senhas (hash salting)
- Resposta clara para erros (credenciais inválidas, conta não encontrada)
- API REST simples para integração com frontend
- Testes automatizados básicos (unit + integração)

## Business Rules

- E-mail deve ser único por usuário
- Senha mínima: 8 caracteres (recomendação inicial)
- Conta bloqueada temporariamente após N tentativas de login falhas (configurável)
- Sessões expiram após TTL configurável

## Inputs

- POST /register { email, password }
- POST /login { email, password }
- POST /logout (requisição autenticada)

## Outputs

- 200 OK + sessão válida (cookie HttpOnly ou token) em caso de sucesso
- 4xx com mensagem padronizada em caso de erro

## Edge Cases

- Registro com e-mail já existente
- Tentativas repetidas de login (brute force)
- Recuperação/alteração de senha não implementada em v1 (documentado)
- Ataques de timing quando comparando credenciais

## Security Requirements

- Hash de senha com bcrypt (salt) ou equivalente aprovado
- Uso de cookie HttpOnly + Secure para sessão ou JWT com short TTL
- Proteção básica contra brute-force (rate limiting / lockout)
- Nunca retornar se o e-mail existe em mensagens públicas (mensagens genéricas)

## Data Model (v1)

- users:
  - id (uuid)
  - email (string, unique)
  - password_hash (string)
  - created_at, updated_at
  - failed_login_count, locked_until (opcional)

## Constraints

- v1 não integra provedores externos (OAuth) — foco em data-first, self-hosted auth
- Deve ser possível implementar em stacks leves (Node/Express + Postgres) ou equivalentes

## Acceptance Criteria

- Um usuário pode se registrar e depois autenticar com as mesmas credenciais
- Senhas são persistidas apenas como hash verificável
- Tentativas de login falhas incrementam contador e acionam lockout após limite configurável
- Endpoints documentados e testes automatizados cobrindo fluxos principais

## Next steps / open questions

- Definir TTL da sessão e estratégia (JWT vs session store)
- Definir política de senha (complexidade)

(spec-v1)
