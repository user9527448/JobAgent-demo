import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

const typescriptFiles = ["src/**/*.{ts,tsx}", "vite.config.ts"];

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    ...js.configs.recommended,
    files: ["**/*.{js,mjs}"],
    languageOptions: {
      globals: {
        console: "readonly",
        Request: "readonly",
        Response: "readonly",
        URL: "readonly",
      },
    },
  },
  ...tseslint.configs.strict.map((config) => ({
    ...config,
    files: typescriptFiles,
  })),
  {
    files: typescriptFiles,
    languageOptions: {
      globals: {
        AbortController: "readonly",
        DOMException: "readonly",
        document: "readonly",
        fetch: "readonly",
        HTMLElement: "readonly",
        Intl: "readonly",
        Request: "readonly",
        Response: "readonly",
        URL: "readonly",
        window: "readonly",
      },
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
    },
  },
);
