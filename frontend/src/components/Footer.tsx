// The credits every page shows. The background picture's licence asks for "Designed by Magnific" with a
// link, clearly visible. The open timetables' licences ask for their sources to be credited (with the
// licence), so they are written here, always visible, not loaded with the access code. The same list
// lives in backend/app/trains/feeds.py. The map's country shapes come from Natural Earth (public domain).

const TIMETABLES = [
  { source: "Eurostar", licence: "Licence Ouverte 2.0", url: "https://www.etalab.gouv.fr/licence-ouverte-open-licence/" },
  { source: "SNCF Voyageurs", licence: "ODbL", url: "https://opendatacommons.org/licenses/odbl/" },
  { source: "DELFI e.V. via gtfs.de", licence: "CC BY 4.0", url: "https://creativecommons.org/licenses/by/4.0/" },
  { source: "NMBS/SNCB", licence: null, url: null },
];

const link = "text-gold underline underline-offset-2 hover:text-snow";

export default function Footer() {
  return (
    <footer className="relative z-10 space-y-1 px-4 py-3 text-center text-sm text-snow/85">
      <p>
        Train timetables:{" "}
        {TIMETABLES.map((t, n) => (
          <span key={t.source}>
            {n > 0 && " · "}
            {t.source}
            {t.licence && t.url && (
              <> (<a href={t.url} target="_blank" rel="noopener noreferrer" className={link}>{t.licence}</a>)</>
            )}
          </span>
        ))}
      </p>
      <p>
        Map shapes:{" "}
        <a href="https://www.naturalearthdata.com" target="_blank" rel="noopener noreferrer" className={link}>
          Natural Earth
        </a>
        {" · "}Background designed by{" "}
        <a href="https://www.magnific.com" target="_blank" rel="noopener noreferrer" className={`font-semibold ${link}`}>
          Magnific
        </a>
      </p>
    </footer>
  );
}
