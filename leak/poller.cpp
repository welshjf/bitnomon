#include <QtCore>
#include <QtNetwork>

class Poller : public QObject
{ Q_OBJECT

public slots:
	void start() {
		QNetworkRequest request(m_url);
		m_reply = m_manager.get(QNetworkRequest(QUrl("http://localhost:5000/")));
		connect(m_reply, SIGNAL(finished()), this, SLOT(readReply()));
		connect(m_reply, SIGNAL(error(QNetworkReply::NetworkError)),
				this, SLOT(error(QNetworkReply::NetworkError)));
	}

	void readReply() {
		m_reply->readAll();
		//m_reply->deleteLater();
		QTimer::singleShot(10, this, SLOT(start()));
	}

	void error(QNetworkReply::NetworkError) {
		m_reply->disconnect();
		qDebug() << "Error:" << m_reply->errorString();
		m_reply->deleteLater();
		qApp->quit();
	}

private:
	QNetworkAccessManager m_manager;
	QUrl m_url;
	QNetworkReply *m_reply;
};

int main (int argc, char *argv[]) {
	QCoreApplication app(argc, argv);
	Poller p;
	p.start();
	return app.exec();
}

#include "poller.moc"
