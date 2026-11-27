export class ApiError extends Error {
  code: string
  status: number
  current_revision?: number
  constructor(code: string, message: string, status = 0, current_revision?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.current_revision = current_revision
  }
}
