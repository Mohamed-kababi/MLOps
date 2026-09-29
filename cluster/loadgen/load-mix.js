import http from 'k6/http';
import { check } from 'k6';

const rows = JSON.parse(open('/scripts/rows.json'));

export const options = {
  scenarios: {
    steady: { executor: 'constant-arrival-rate', rate: 10, timeUnit: '1s',
              duration: '20m', preAllocatedVUs: 10, maxVUs: 50 },
  },
};

export default function () {
  const row = rows[Math.floor(Math.random() * rows.length)];
  const res = http.post('http://model-server/predict', JSON.stringify({ rows: [row] }),
                        { headers: { 'Content-Type': 'application/json' } });
  check(res, { 'status 200': (r) => r.status === 200 });
}
