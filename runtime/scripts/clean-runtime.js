import fs from "node:fs";
import path from "node:path";

for (const target of ["artifacts-local", "cache", "artifacts"]) {
  const fullPath = path.join(process.cwd(), target);
  if (fs.existsSync(fullPath)) {
    fs.rmSync(fullPath, { recursive: true, force: true });
    console.log(`Removed ${fullPath}`);
  }
}
