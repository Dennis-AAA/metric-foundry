import { spawn } from "node:child_process";

const port = process.env.PORT || "43180";
const child = spawn("npx", ["next", "start", "--hostname", "0.0.0.0", "--port", port], {
  stdio: "inherit",
  env: process.env,
});
child.on("exit", (code) => process.exit(code ?? 1));
