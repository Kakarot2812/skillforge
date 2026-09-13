import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith(".") || specifier.startsWith("file:") || specifier.startsWith("@/")) {
    let resolvedSpecifier = specifier;
    if (specifier.startsWith("@/")) {
      const srcPath = path.resolve(process.cwd(), "src", specifier.slice(2));
      resolvedSpecifier = pathToFileURL(srcPath).href;
    }
    try {
      return await nextResolve(resolvedSpecifier, context);
    } catch (err) {
      if (err.code === "ERR_MODULE_NOT_FOUND") {
        const url = new URL(resolvedSpecifier, context.parentURL);
        const filePath = fileURLToPath(url);
        for (const ext of [".ts", ".tsx", ".js", ".mjs", "/index.ts", "/index.js"]) {
          if (existsSync(filePath + ext)) {
            return nextResolve(pathToFileURL(filePath + ext).href, context);
          }
        }
      }
      throw err;
    }
  }
  return nextResolve(specifier, context);
}
