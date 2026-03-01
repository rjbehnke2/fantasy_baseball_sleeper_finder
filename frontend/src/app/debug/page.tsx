"use client";

import { useEffect, useState } from "react";

interface TestResult {
  name: string;
  status: "pending" | "ok" | "error";
  detail?: string;
  data?: unknown;
}

export default function DebugPage() {
  const [tests, setTests] = useState<TestResult[]>([]);

  useEffect(() => {
    runDiagnostics();
  }, []);

  async function runDiagnostics() {
    const results: TestResult[] = [];

    // Test 1: Backend health via Next.js proxy
    try {
      const res = await fetch("/health");
      const data = await res.json();
      results.push({
        name: "Backend health (via proxy /health)",
        status: res.ok ? "ok" : "error",
        detail: `HTTP ${res.status}`,
        data,
      });
    } catch (e) {
      results.push({
        name: "Backend health (via proxy /health)",
        status: "error",
        detail: String(e),
      });
    }
    setTests([...results]);

    // Test 2: Debug endpoint via proxy
    try {
      const res = await fetch("/api/v1/debug/check");
      const text = await res.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = text.substring(0, 500);
      }
      results.push({
        name: "Debug check (via proxy /api/v1/debug/check)",
        status: res.ok ? "ok" : "error",
        detail: `HTTP ${res.status}`,
        data,
      });
    } catch (e) {
      results.push({
        name: "Debug check (via proxy /api/v1/debug/check)",
        status: "error",
        detail: String(e),
      });
    }
    setTests([...results]);

    // Test 3: Rankings endpoint via proxy
    try {
      const res = await fetch("/api/v1/rankings?limit=3");
      const text = await res.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = `JSON parse failed. Raw (first 500 chars): ${text.substring(0, 500)}`;
      }
      results.push({
        name: "Rankings API (via proxy /api/v1/rankings?limit=3)",
        status: res.ok ? "ok" : "error",
        detail: `HTTP ${res.status}, body length=${text.length}`,
        data,
      });
    } catch (e) {
      results.push({
        name: "Rankings API (via proxy /api/v1/rankings?limit=3)",
        status: "error",
        detail: String(e),
      });
    }
    setTests([...results]);

    // Test 4: Direct backend call (bypassing Next.js proxy)
    try {
      const res = await fetch("http://localhost:8000/api/v1/rankings?limit=3");
      const text = await res.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = `JSON parse failed. Raw (first 500 chars): ${text.substring(0, 500)}`;
      }
      results.push({
        name: "Rankings API DIRECT (http://localhost:8000/api/v1/rankings?limit=3)",
        status: res.ok ? "ok" : "error",
        detail: `HTTP ${res.status}, body length=${text.length}`,
        data,
      });
    } catch (e) {
      results.push({
        name: "Rankings API DIRECT (http://localhost:8000/api/v1/rankings?limit=3)",
        status: "error",
        detail: String(e),
      });
    }
    setTests([...results]);

    // Test 5: Sleepers endpoint
    try {
      const res = await fetch("/api/v1/rankings/sleepers?limit=3");
      const text = await res.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = `JSON parse failed. Raw (first 500 chars): ${text.substring(0, 500)}`;
      }
      results.push({
        name: "Sleepers API (via proxy /api/v1/rankings/sleepers?limit=3)",
        status: res.ok ? "ok" : "error",
        detail: `HTTP ${res.status}, body length=${text.length}`,
        data,
      });
    } catch (e) {
      results.push({
        name: "Sleepers API (via proxy)",
        status: "error",
        detail: String(e),
      });
    }
    setTests([...results]);
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">API Diagnostics</h1>
      <p className="text-sm text-gray-500 mb-6">
        Tests API connectivity through the Next.js proxy and directly.
      </p>
      <button
        onClick={runDiagnostics}
        className="mb-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Re-run Tests
      </button>
      <div className="space-y-4">
        {tests.map((t, i) => (
          <div
            key={i}
            className={`border rounded p-4 ${
              t.status === "ok"
                ? "border-green-400 bg-green-50"
                : t.status === "error"
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300"
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`font-mono text-sm px-2 py-0.5 rounded ${
                  t.status === "ok"
                    ? "bg-green-200 text-green-800"
                    : t.status === "error"
                      ? "bg-red-200 text-red-800"
                      : "bg-gray-200"
                }`}
              >
                {t.status.toUpperCase()}
              </span>
              <span className="font-medium">{t.name}</span>
            </div>
            {t.detail && (
              <p className="text-sm text-gray-600 mt-1">{t.detail}</p>
            )}
            {t.data != null && (
              <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto max-h-48">
                {typeof t.data === "string"
                  ? t.data
                  : JSON.stringify(t.data, null, 2)}
              </pre>
            )}
          </div>
        ))}
        {tests.length === 0 && (
          <p className="text-gray-400">Running diagnostics...</p>
        )}
      </div>
    </div>
  );
}
