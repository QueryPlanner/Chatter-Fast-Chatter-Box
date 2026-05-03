import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1A73E8",
        'text-main': "#202124",
        surface: "#FFFFFF",
        'surface-warm': "#F5DEC3",
        'surface-blue-light': "#D3E3FD",
        'border-dark': "#1F1F1F",
        'google-blue': "#4285F4",
        'google-red': "#EA4335",
        'google-yellow': "#FBBC05",
        'google-green': "#34A853",
      },
      fontFamily: {
        sans: ['Google Sans', 'sans-serif'],
      },
      borderRadius: {
        sm: '8px',
        md: '16px',
        lg: '24px',
        full: '9999px',
      },
    },
  },
  plugins: [],
};

export default config;