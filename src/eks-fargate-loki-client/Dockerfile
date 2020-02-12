FROM clearlinux/python:3.8.0
ENV LANG=C.UTF-8
RUN mkdir /logger
WORKDIR /logger
COPY requirements.txt /logger
RUN pip install -r requirements.txt
COPY *.py /logger
CMD ["python","handler.py"]