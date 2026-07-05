interface Window {
  katex: {
    renderToString(
      tex: string,
      options?: { displayMode?: boolean; throwOnError?: boolean },
    ): string;
  };
}
