import './AboutPage.css';

export default function AboutPage() {
  return (
    <div className="about-page">
      <h1>
        About Solmu
      </h1>
      <div className="about-content">
        <p>
          Solmu - Finnish for "knot" - is an attempt to tie together all the available web sources 
          and preserve the full scope of classical guitar repertoire. It's meant to connect us more 
          deeply to our repertoire and make it accessible to anyone looking for their next piece.
        </p>
        <p>
          The idea for this database came about when I was a classical guitar student trying to pick repertoire for my recitals. 
          I was always looking for something fresh to complement the 100 or so canonical pieces 
          that everyone seems to play. But finding those hidden gems was frustrating - the information 
          was scattered across different corners of the web, buried in forums, obscure databases, 
          and personal collections.
        </p>
        <p>
          What made it worse was how algorithms heavily weighted already popular music when searching. 
          The same pieces kept surfacing while countless others remained invisible. New music would get 
          played once and then forgotten - no archive, no trace. It struck me that no one even knew how 
          many published guitar works actually existed.
        </p>
        <p>
          I wanted to create a centralized repository without the bias of algorithms. A place where new 
          music sits right alongside the canon, where a composer with one work has the same visibility 
          as Sor or Tárrega. This gives performers the freedom to discover and choose based on their 
          own tastes and needs, not what's trending or what an algorithm thinks they should hear.
        </p>
      </div>
    </div>
  );
}
