import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync, spawn } from "node:child_process";

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith("--")) {
      continue;
    }
    const key = current.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      parsed[key] = true;
    } else {
      parsed[key] = next;
      index += 1;
    }
  }
  return parsed;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function requestOk(url) {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      const ok = res.statusCode && res.statusCode >= 200 && res.statusCode < 400;
      res.resume();
      resolve(Boolean(ok));
    });
    req.on("error", () => resolve(false));
    req.setTimeout(1500, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function ensureLocalServer({ runtimeRoot, port, pythonBin }) {
  const healthUrl = `http://127.0.0.1:${port}/claim.html`;
  if (await requestOk(healthUrl)) {
    return healthUrl;
  }

  const child = spawn(
    pythonBin,
    ["-m", "http.server", String(port), "--directory", "dapp"],
    {
      cwd: runtimeRoot,
      detached: true,
      stdio: "ignore",
      windowsHide: true
    }
  );
  child.unref();

  for (let attempt = 0; attempt < 10; attempt += 1) {
    await wait(700);
    if (await requestOk(healthUrl)) {
      return healthUrl;
    }
  }
  throw new Error(`Local claim DApp server did not start on ${healthUrl}`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const runtimeRoot = path.resolve(scriptDir, "..");
  const port = Number(args.port || process.env.CLAIM_DAPP_PORT || 8787);
  const pythonBin = args["python-bin"] || process.env.PYTHON_BIN || "python";
  const baseUrl = await ensureLocalServer({ runtimeRoot, port, pythonBin });

  const generateScript = path.join(runtimeRoot, "scripts", "generate-claim-link.js");
  const passthrough = [];
  for (const [key, value] of Object.entries(args)) {
    if (key === "port" || key === "python-bin") {
      continue;
    }
    passthrough.push(`--${key}`);
    if (value !== true) {
      passthrough.push(String(value));
    }
  }

  const stdout = execFileSync(
    process.execPath,
    [generateScript, ...passthrough, "--base-url", baseUrl],
    { cwd: runtimeRoot, encoding: "utf8" }
  );
  const payload = JSON.parse(stdout);
  payload.localServer = baseUrl;
  console.log(JSON.stringify(payload, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
