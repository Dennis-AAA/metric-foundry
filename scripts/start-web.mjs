import { spawn } from "node:child_process";
import path from "node:path";

const port = process.env.PORT || "8080";
const nextBin = path.join(process.cwd(), "node_modules", "next", "dist", "bin", "next");
const child = spawn(process.execPath, [nextBin, "start", "--hostname", "0.0.0.0", "--port", port], {
  stdio: "inherit",
  env: process.env,
});
child.on("exit", (code) => process.exit(code ?? 1));
