// The credits every page shows. The background picture's licence asks for "Designed by Magnific"
// with a link, clearly visible; the timetable credits join them once the website loads options.
export default function Footer() {
  return (
    <footer className="relative z-10 px-4 py-3 text-center text-sm text-snow/85">
      Background designed by{" "}
      <a href="https://www.magnific.com" target="_blank" rel="noopener noreferrer"
         className="font-semibold text-gold underline underline-offset-2 hover:text-snow">
        Magnific
      </a>
    </footer>
  );
}
