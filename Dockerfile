FROM python

COPY . /gokgs

WORKDIR /gokgs
RUN pip3 install .

EXPOSE 8081

CMD ["gokgs"]
