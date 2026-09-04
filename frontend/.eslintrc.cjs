module.exports = {
  root: true,
  env: { browser: true, es2021: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-refresh"],
  ignorePatterns: ["dist", "node_modules", ".eslintrc.cjs", "vite.config.ts"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/ban-ts-comment": "off",
    "no-empty": ["error", { allowEmptyCatch: true }],
  },
  overrides: [
    {
      // Generated primitives from `shadcn` / `@ai-elements` — not hand-maintained.
      files: ["src/components/ui/**", "src/components/ai-elements/**"],
      rules: {
        "react-refresh/only-export-components": "off",
        "@typescript-eslint/no-unused-vars": "off",
        "react-hooks/rules-of-hooks": "off",
      },
    },
  ],
};
