/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

export class AuthenticationError extends Error {
  constructor(message: string) {
    super(message)
  }
}

export class PermissionError extends Error {
  constructor(message: string) {
    super(message)
  }
}

export class APIServerError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export class RequestError extends Error {
  constructor(message: string) {
    super(message)
  }
}

export class CanceledRequestError extends Error {
  constructor(message: string) {
    super(message)
  }
}
