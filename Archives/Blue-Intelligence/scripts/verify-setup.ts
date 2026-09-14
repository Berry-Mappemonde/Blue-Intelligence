#!/usr/bin/env tsx
/**
 * Vérifie que l'environnement est correctement configuré pour Blue Intelligence.
 * À exécuter après npm install pour valider TensorFlow et better-sqlite3.
 */
import { createRequire } from "module";
const require = createRequire(import.meta.url);

const NODE_MIN = 18;
const NODE_RECOMMENDED = 20;

function checkNodeVersion(): boolean {
  const v = process.version.slice(1).split(".").map(Number);
  const major = v[0] ?? 0;
  if (major < NODE_MIN) {
    console.error(`❌ Node.js ${NODE_MIN}+ requis. Actuel: ${process.version}`);
    return false;
  }
  if (major < NODE_RECOMMENDED) {
    console.warn(`⚠️  Node.js ${NODE_RECOMMENDED} LTS recommandé pour better-sqlite3. Actuel: ${process.version}`);
  } else {
    console.log(`✓ Node.js ${process.version}`);
  }
  return true;
}

function checkBetterSqlite3(): boolean {
  try {
    require("better-sqlite3");
    console.log("✓ better-sqlite3");
    return true;
  } catch (e: any) {
    console.error("❌ better-sqlite3:", e?.message ?? e);
    console.error("   → npm install (ou npm rebuild better-sqlite3)");
    return false;
  }
}

async function checkTensorFlow(): Promise<boolean> {
  try {
    await import("@tensorflow/tfjs");
    const use = await import("@tensorflow-models/universal-sentence-encoder");
    const model = await use.load();
    const tensor = await model.embed(["test"]);
    const arr = await tensor.array();
    tensor.dispose();
    if (Array.isArray(arr) && arr.length > 0) {
      console.log("✓ TensorFlow + Universal Sentence Encoder");
      return true;
    }
  } catch (e: any) {
    console.error("❌ TensorFlow:", e?.message ?? e);
    console.error("   → npm install");
    return false;
  }
  return false;
}

async function main() {
  console.log("Vérification de l'environnement Blue Intelligence\n");
  let ok = true;
  ok = checkNodeVersion() && ok;
  ok = checkBetterSqlite3() && ok;
  ok = (await checkTensorFlow()) && ok;
  console.log("");
  if (ok) {
    console.log("✓ Environnement prêt. Lancez: npm run dev");
  } else {
    console.log("Conseils: npm install puis npm run verify-setup");
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
