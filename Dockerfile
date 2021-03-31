FROM python

COPY . /gokgs

WORKDIR /gokgs
RUN pip3 install .

CMD ["gokgs"]
