demo:	build demo-container


build :
	docker build -t sr-demo .


demo-container:
	docker network create --driver=bridge --subnet=192.168.1.0/24 sr-net
	docker run --name srdemo --rm -t --network=sr-net --ip=192.168.1.2 --dns=8.8.8.8 \
	-p 5001:5001 \
	-p 4200:4200 \
	-p 179:179 \
	-p 5000:5000 \
	--volume `pwd`:/home/demos/sr-demo \
        -i sr-demo bash

term:
	docker run --rm -t --network=sr-net --dns=8.8.8.8 \
	--volume `pwd`:/home/demos/sr-demo \
        -i sr-demo bash

clean:
	docker network rm sr-net
