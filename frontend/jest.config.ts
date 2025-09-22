import nextJest from "next/jest";

const createJestConfig = nextJest({ dir: "./" });

const customJestConfig = {
  testEnvironment: "jest-environment-jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  moduleDirectories: ["node_modules", "<rootDir>/src", "<rootDir>"],
  moduleNameMapper: {
    "^@/components/(.*)$": ["<rootDir>/src/components/$1", "<rootDir>/components/$1"],
    "^@/lib/(.*)$": ["<rootDir>/src/lib/$1", "<rootDir>/lib/$1"],
    "^@/services/(.*)$": "<rootDir>/src/services/$1",
    "^@/types/(.*)$": "<rootDir>/src/types/$1",
    "^@/features/(.*)$": "<rootDir>/src/features/$1",
    "^@/hooks/(.*)$": "<rootDir>/src/hooks/$1",
    "^@/store/(.*)$": "<rootDir>/src/store/$1",
  },
  testMatch: ["<rootDir>/**/__tests__/**/*.(test|spec).[jt]s?(x)"],
};

export default createJestConfig(customJestConfig);
