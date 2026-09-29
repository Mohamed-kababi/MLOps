import http from 'k6/http';
import { check } from 'k6';

const payload = open(__ENV.PAYLOAD);

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',   // open model: no coordinated omission
      rate: Number(__ENV.RATE || 50),
      timeUnit: '1s',
      duration: __ENV.DURATION || '60s',
      preAllocatedVUs: 20,
      maxVUs: 200,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: [`p(95)<${__ENV.P95 || 250}`],
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const res = http.post(__ENV.URL, payload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}
