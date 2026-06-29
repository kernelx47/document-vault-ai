/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            "--tw-prose-body": "#5e537c",
            "--tw-prose-headings": "#281950",
            "--tw-prose-links": "#7c3aed",
            "--tw-prose-bold": "#281950",
            "--tw-prose-code": "#281950",
            "--tw-prose-pre-bg": "#f1f2f9",
            "--tw-prose-pre-code": "#281950",
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            code: {
              backgroundColor: "#f1f2f9",
              padding: "2px 6px",
              borderRadius: "6px",
              fontWeight: "400",
              fontSize: "0.875em",
            },
            a: {
              color: "#7c3aed",
              textDecoration: "underline",
              textDecorationColor: "#e7e6f4",
              textUnderlineOffset: "2px",
              fontWeight: "500",
              "&:hover": { textDecorationColor: "#7c3aed" },
            },
            strong: { fontWeight: "600", color: "#281950" },
            h1: { fontWeight: "500", color: "#281950", fontFamily: "'Source Serif 4', serif", letterSpacing: "-0.025em" },
            h2: { fontWeight: "500", color: "#281950", fontFamily: "'Source Serif 4', serif", letterSpacing: "-0.025em" },
            h3: { fontWeight: "500", color: "#281950", fontFamily: "'Source Serif 4', serif", letterSpacing: "-0.025em" },
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
