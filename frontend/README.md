# Frontend

Next.js (TypeScript, Tailwind, shadcn/ui, MapLibre): the MerryMapped web app.

Run it: `npm install` once, then `npm run dev` and open http://localhost:3000.

## Background picture (download it yourself)

The winter night background picture is **not included in this repository because of licensing
restrictions**: it is a free Magnific picture, and its licence allows using it on the website
(with the credit "Designed by Magnific" and a link, shown in the footer) but forbids making the
file available for others to download.

To set it up:

1. Download the picture from its Magnific page:
   https://www.magnific.com/free-photo/winter-night-background-festive-holiday-design_20122953.htm
2. Make a web copy 1920 pixels wide and save it as `public/backgrounds/winter-night.jpg`.
   On a Mac:

       mkdir -p public/backgrounds
       sips -Z 1920 -s format jpeg -s formatOptions 62 <downloaded file> --out public/backgrounds/winter-night.jpg

   On other computers, any image tool that resizes to 1920 pixels wide and saves as JPEG works.

Without the picture, the site still works and shows a plain teal sky.
