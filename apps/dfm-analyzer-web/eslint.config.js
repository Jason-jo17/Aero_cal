import { nextJsConfig } from "@repo/eslint-config/next-js";

/** @type {import("eslint").Linter.Config[]} */
export default [
  ...nextJsConfig,
  {
    // react-three-fiber renders Three.js objects as JSX intrinsics
    // (geometry, castShadow, roughness, metalness, ...) that aren't real DOM
    // props; the DOM-oriented no-unknown-property rule doesn't know them.
    files: ["**/*.tsx"],
    rules: {
      "react/no-unknown-property": [
        "warn",
        {
          ignore: ["castShadow", "receiveShadow", "roughness", "metalness", "geometry", "args", "intensity"],
        },
      ],
    },
  },
];
