import "./globals.css";

export const metadata = {
  title: "KAVI Plugin Doctor",
  description: "Audit ChatGPT Agent Plugins and remote MCP capability surfaces before shipping.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
