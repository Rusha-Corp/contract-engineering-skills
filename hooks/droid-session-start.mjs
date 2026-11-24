import { spawnSync } from "node:child_process";

const command = process.env.TM_CONTEXT_COMMAND || "tm";
const timeoutSeconds = Number(process.env.TM_CONTEXT_TIMEOUT_SECONDS || "8");
if (!Number.isInteger(timeoutSeconds) || timeoutSeconds < 1 || timeoutSeconds > 10) {
  process.exit(0);
}

const result = spawnSync(command, ["context", "droid-hook"], {
  encoding: "utf8",
  stdio: ["inherit", "pipe", "ignore"],
  shell: false,
  timeout: timeoutSeconds * 1000,
  maxBuffer: 1_000_000,
  windowsHide: true,
});
if (!result.error && result.status === 0 && typeof result.stdout === "string") {
  process.stdout.write(result.stdout);
}
