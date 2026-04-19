import { describe, it, expect, spyOn, mock } from "bun:test";
import { ErrorHandler } from "../src/errors.ts";

// Prevent process.exit from actually exiting
const exitSpy = spyOn(process, "exit").mockImplementation((() => {
  throw new Error("process.exit called");
}) as never);

const errorSpy = spyOn(console, "error").mockImplementation(() => {});

describe("ErrorHandler.handle", () => {
  it("prints skill-not-found message for 404 errors", () => {
    expect(() => ErrorHandler.handle(new Error("Not Found"))).toThrow();
    expect(errorSpy).toHaveBeenCalledWith(
      expect.stringContaining("Skill not found"),
    );
  });

  it("prints skill-not-found message for 404 in message", () => {
    expect(() => ErrorHandler.handle(new Error("404 response"))).toThrow();
    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining("Skill not found"));
  });

  it("prints access-denied message for 403 errors", () => {
    expect(() => ErrorHandler.handle(new Error("403 Forbidden"))).toThrow();
    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining("Access denied"));
  });

  it("prints network error message for ENOTFOUND", () => {
    expect(() => ErrorHandler.handle(new Error("ENOTFOUND api.github.com"))).toThrow();
    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("prints network error message for fetch failed", () => {
    expect(() => ErrorHandler.handle(new Error("fetch failed"))).toThrow();
    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("prints the raw message for unknown errors", () => {
    expect(() => ErrorHandler.handle(new Error("something weird"))).toThrow();
    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining("something weird"));
  });

  it("handles non-Error values", () => {
    expect(() => ErrorHandler.handle("string error")).toThrow();
    expect(errorSpy).toHaveBeenCalledWith("An unexpected error occurred.");
  });

  it("calls process.exit(1)", () => {
    expect(() => ErrorHandler.handle(new Error("x"))).toThrow();
    expect(exitSpy).toHaveBeenCalledWith(1);
  });
});
