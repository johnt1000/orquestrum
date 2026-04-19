import request from 'supertest';
import app from '../server.js';

describe('health', () => {
  it('returns 200', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toBe(200);
    expect(res.body).toHaveProperty('status', 'ok');
  });
});
