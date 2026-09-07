# Serves the Flux whitepaper as a static site.
#
# The root path is the combined document: the 16-page short paper first, the
# full paper behind it. PDFs are served as application/pdf with an inline
# disposition, so they open in the browser rather than downloading.
#
#   docker build -t runonflux/fluxwhitepaper:latest .
#   docker run --rm -p 8080:8080 runonflux/fluxwhitepaper:latest
#   open http://localhost:8080/
#
# To update the application running on Flux: rebuild, push the tag the app
# specification names, and redeploy. Nothing here needs a LaTeX toolchain --
# the PDFs are committed, so a build is a copy.

FROM nginx:alpine

LABEL org.opencontainers.image.title="Flux v9 whitepaper" \
      org.opencontainers.image.description="Flux v9: A Decentralized Cloud for Autonomous Compute" \
      org.opencontainers.image.source="https://github.com/RunOnFlux/fluxwhitepaper" \
      org.opencontainers.image.licenses="See repository"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY FluxWhitepaper-Combined.pdf \
     FluxWhitepaper.pdf \
     FluxWhitepaper-Short.pdf \
     /usr/share/nginx/html/

EXPOSE 8080

# Cheap liveness probe: /health returns a few bytes, so a health check never
# pulls the 3.8 MB PDF.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
