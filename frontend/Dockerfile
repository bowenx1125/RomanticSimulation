FROM docker.m.daocloud.io/library/node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN npm run build
RUN mkdir -p .next/standalone/.next \
  && cp -R .next/static .next/standalone/.next/static \
  && if [ -d public ]; then cp -R public .next/standalone/public; fi

CMD ["node", ".next/standalone/server.js"]
